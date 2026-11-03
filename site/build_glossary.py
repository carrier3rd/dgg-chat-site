#!/usr/bin/env python3
"""Live DGG chat glossary: find terms chat is using now, add context, publish to the site.

Runs hourly (dgg-glossary.timer). Writes <out>/glossary.json for the site and keeps its own state in
~/socialscope_data/glossary_state.json.

What gets published, per term: counts and rates, a 14-day trend, archive history (2014-2020), words and emotes
it appears with, up to two example lines, and a definition.

Safeguards (definitions publish without human review, so these are automatic):
- A word is never an entry if it matches a chatter's name: each candidate is hashed with the logger's salt and
  dropped if the hash belongs to any chatter seen live or in the 2014-2020 DGG archive. No names are stored.
- Example lines are only lines that 3+ different chatters sent word for word (copypastas and common
  reactions), at most 120 characters, with no name, link, @, long number or blocked word.
- Terms matching the slur blocklist never become entries.
- Definitions come first from the project glossary (data/glossary.csv), then the DGG wiki
  (data/dgg_emotes.csv), and only then from Claude. Claude also judges each new term; anything it flags as a slur,
  harassment, sexual content or a claim about a real person's private life is held back entirely (not
  published) and listed in the state file.
- Sample messages sent to the model have names replaced with [user] and links removed. They are not published.

Definitions without an API key: each run writes the terms that need a meaning, with sanitized sample lines, to
~/socialscope_data/glossary_pending.json (private, never published). A daily scheduled Claude task reads it and
writes ~/socialscope_data/glossary_definitions.json, which the next run applies (sensitive ones are held).
Optional: with ANTHROPIC_API_KEY set, the script drafts definitions itself through the API instead.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import hmac
import json
import math
import os
import re
import urllib.error
import urllib.request

csv.field_size_limit(10**8)
H = os.path.expanduser
DAYFILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl(\.gz)?$")
TOK = re.compile(r"[a-z0-9_']+")
MODEL = "claude-sonnet-5-5"
API = "https://api.anthropic.com/v1/messages"

MIN_USERS_24H = 10        # distinct chatters in the last 24 hours
MIN_COUNT_24H = 20
MIN_LIFT = 5.0            # 24h rate vs the larger of the 30-day and archive baselines
MAX_TRENDING = 25
TRACK_DAYS = 30           # keep showing a term this long after it last trended
MAX_CALLS_PER_RUN = 10
REDRAFT_DAYS = 7

BLOCK = re.compile(r"(n[i1!]gg|f[a@]gg?(ot)?s?\b|tr[a@]nn(y|ie)|retard|k[i1]ke|ch[i1]nk|sp[i1]c\b|beaner|wetback|"
                   r"\bcoons?\b|dyke|g[o0]{2}k|\bkys\b|rape)", re.I)
URLISH = re.compile(r"(https?://|www\.|\.com\b|\.gg/|\.tv/|@)", re.I)
LONGNUM = re.compile(r"\d{5,}")
JUNK = {"http", "https", "www", "com", "gg", "tv", "lol", "lmao", "yes", "yeah", "nah", "okay", "chat", "guys",
        "bro", "dude", "man", "lmfao", "haha", "omg", "wtf", "imo", "tbh", "idk", "gonna", "wanna", "gotta"}
STOP = set("""a about above after again against all also am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each even ever every
few for from further get gets getting got had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself just know let let's like
literally make makes many maybe me mean might more most much must mustn't my myself never new no nor not now of off oh on
once one only or other ought our ours ourselves out over own people pretty really right said same say says see she she'd
she'll she's should shouldn't so some something still such sure take than that that's the their theirs them themselves then
there there's these they they'd they'll they're they've thing things think this those though through time to too two under
until up us very want was wasn't way we we'd we'll we're we've well were weren't what what's when when's where where's which
while who who's whom why why's will with won't would wouldn't yet you you'd you'll you're you've your yours yourself
yourselves going thats dont im cant didnt doesnt isnt wasnt youre ive ill hes shes theyre whats lets wont""".split())
LINK = re.compile(r"(https?://\S+|www\.\S+|\S+\.(com|gg|tv|be|io|org|net|co)(/\S*)?)", re.I)


def h16(salt, s):
    return hmac.new(salt, s.lower().encode(), hashlib.sha256).hexdigest()[:16]


def read_live(live, since_ms):
    days = sorted({m.group(1) for fn in os.listdir(live) if (m := DAYFILE.match(fn))})
    for d in days:
        end_ms = (dt.datetime.fromisoformat(d + "T00:00:00+00:00") + dt.timedelta(days=1)).timestamp() * 1000
        if end_ms < since_ms:
            continue
        for suffix in (".jsonl.gz", ".jsonl"):
            p = os.path.join(live, d + suffix)
            if os.path.exists(p):
                op = gzip.open if suffix.endswith(".gz") else open
                with op(p, "rt", encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if r.get("ts", 0) >= since_ms and "bot" not in (r.get("flags") or []):
                            yield r


def load_archive(agg):
    """Lower-cased DGG archive token counts per year, total messages per year, and chatter hashes."""
    rates = collections.defaultdict(dict)   # DGG history, for the archive line on each entry
    base = collections.Counter()            # highest yearly rate in DGG or Destiny's Twitch chat, for the baseline
    n = collections.Counter()
    for ch in ("Destinygg", "Destiny"):
        tok_path = os.path.join(agg, ch, "tokens.tsv")
        if not os.path.exists(tok_path):
            continue
        cn = collections.Counter()
        with open(os.path.join(agg, ch, "monthly.csv")) as f:
            for r in csv.DictReader(f):
                cn[r["month"][:4]] += int(r["messages"])
        acc = collections.defaultdict(collections.Counter)
        with open(tok_path) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                acc[r["token"].lower()][r["year"]] += int(r["count"])
        for t, ys in acc.items():
            yr = {y: c / cn[y] for y, c in ys.items() if cn[y] >= 100000}
            if yr:
                base[t] = max(base[t], max(yr.values()))
                if ch == "Destinygg":
                    rates[t] = yr
        if ch == "Destinygg":
            n = cn
    names = set()
    up = os.path.join(agg, "Destinygg", "user_years.tsv")
    if os.path.exists(up):
        with open(up) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["year"] >= "2019":  # recent archive regulars only, to limit collisions with ordinary words
                    names.add(r["user_hash"])
    return rates, base, n, names


def load_meanings(glossary_csv, emotes_csv):
    m = {}
    if os.path.exists(glossary_csv):
        for r in csv.DictReader(open(glossary_csv, encoding="utf-8")):
            mean = (r.get("meaning") or "").strip()
            mean = re.split(r"\s+Chat history:", mean)[0].strip()  # project notes, not part of the meaning
            if mean and not re.search(r"\ba destiny\.gg emote\b", mean):  # skip auto-filled emote stubs
                m[r["term"].strip().lower()] = (mean, "Project glossary")
    if os.path.exists(emotes_csv):  # for emotes the DGG wiki wins
        for r in csv.DictReader(open(emotes_csv, encoding="utf-8")):
            if (r.get("meaning") or "").strip():
                m[r["emote"].lower()] = (r["meaning"].strip(), "DGG wiki")
    return m


def call_claude(key, term, info, samples):
    prompt = f"""You are writing one entry for a public glossary of destiny.gg (DGG) livestream chat, a community
around the political streamer Destiny. The entry is published automatically, so be careful and neutral.

Term: {term}
Kind guess: {info['kind']}
Use in the last 24 hours: {info['messages_24h']} messages from {info['chatters_24h']} chatters,
{info['lift']}x its usual rate. Archive history (2014-2020 DGG chat): {info['archive_note']}.
Words and emotes it appears with: {', '.join(info['co']) or 'none'}.

Recent chat lines using it (names replaced with [user]; these are context for you and will not be published):
{chr(10).join('- ' + s for s in samples)}

Reply with JSON only, no prose:
{{"definition": "<one or two plain sentences on what the term means or refers to in DGG chat, and how chat is using it
right now; say 'appears to' when unsure; no claims of fact about real people beyond who or what the term refers to>",
"kind": "<emote | nickname | meme | phrase | reference | person | event | other>",
"sensitive": <true if the term is a slur or slur substitute, harassment or a pile-on aimed at someone, sexual content,
or an allegation about a real person's private life, health or crimes; otherwise false>,
"reason": "<short reason if sensitive, else empty>"}}"""
    body = json.dumps({"model": MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API, data=body, headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.load(r)
    text = "".join(c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    out = json.loads(m.group(0))
    return {"definition": str(out.get("definition", "")).strip()[:400], "kind": str(out.get("kind", "other"))[:20],
            "sensitive": bool(out.get("sensitive")), "reason": str(out.get("reason", ""))[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default=H("~/socialscope_data/dgg_live"))
    ap.add_argument("--agg", default=H("~/socialscope_data/orl_agg"))
    ap.add_argument("--salt-file", default=H("~/socialscope/.socialscope_salt"))
    ap.add_argument("--emotes", default=H("~/socialscope_data/dgg_chat/emotes.json"))
    ap.add_argument("--emote-meanings", default=H("~/socialscope/data/dgg_emotes.csv"))
    ap.add_argument("--glossary", default=H("~/socialscope/data/glossary.csv"))
    ap.add_argument("--state", default=H("~/socialscope_data/glossary_state.json"))
    ap.add_argument("--definitions", default=H("~/socialscope_data/glossary_definitions.json"))
    ap.add_argument("--pending", default=H("~/socialscope_data/glossary_pending.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true", help="no API calls; print what would be drafted")
    a = ap.parse_args()

    salt = open(H(a.salt_file)).read().strip().encode()
    emotes = {e["prefix"] for e in json.load(open(H(a.emotes)))}
    emotes_low = {e.lower(): e for e in emotes}
    meanings = load_meanings(H(a.glossary), H(a.emote_meanings))
    rates, arch_base, arch_n, names = load_archive(H(a.agg))
    state = json.load(open(a.state)) if os.path.exists(a.state) else {"terms": {}}
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    try:
        defs = json.load(open(a.definitions)).get("terms", {})
    except (OSError, ValueError):
        defs = {}
    pending = []

    now = dt.datetime.now(dt.timezone.utc)
    now_ms = now.timestamp() * 1000
    t24, t7d, t30 = now_ms - 86400e3, now_ms - 7 * 86400e3, now_ms - 30 * 86400e3

    n24 = nbase = 0
    c24, cbase = collections.Counter(), collections.Counter()
    first24 = collections.Counter()  # times a word opened a message: replies start with the person's name
    u24 = collections.defaultdict(set)
    daily = collections.defaultdict(collections.Counter)
    day_n = collections.Counter()
    recent = []  # (ts, user, text, token set) for the last 7 days
    for r in read_live(H(a.live), t30):
        names.add(r.get("u"))
        text = r.get("text") or ""
        seq = TOK.findall(LINK.sub(" ", text).lower())
        toks = set(seq) | {w.lower() for w in text.split() if w in emotes}
        toks |= {f"{x} {y}" for x, y in zip(seq, seq[1:])}
        d = dt.datetime.fromtimestamp(r["ts"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
        day_n[d] += 1
        if r["ts"] >= t24:
            n24 += 1
            c24.update(toks)
            if seq:
                first24[seq[0]] += 1
            for t in toks:
                u24[t].add(r.get("u"))
        else:
            nbase += 1
            cbase.update(toks)
        if r["ts"] >= now_ms - 14 * 86400e3:
            daily[d].update(toks)
        if r["ts"] >= t7d:
            recent.append((r["ts"], r.get("u"), text, toks))

    def is_name(t):
        return any(h16(salt, part) in names for part in t.split(" "))

    def archive_rate(t):
        return arch_base.get(t, 0.0)

    def ok_term(t):
        if t in emotes_low or t in meanings:
            return not BLOCK.search(t)  # known emotes and glossary terms skip the name check
        if len(t) < 3 or t in JUNK or t in STOP or t.isdigit() or BLOCK.search(t) or URLISH.search(t):
            return False
        if re.search(r"\d", t) and not t.isalpha() and len(t) > 6:  # IDs, codes, link remnants
            return False
        if " " in t and (any(p in JUNK or len(p) < 2 for p in t.split(" ")) or all(p in STOP for p in t.split(" "))):
            return False
        return not is_name(t)

    # ---- trending candidates
    cands = []
    if n24:
        floor = 1 / 200000
        for t, c in c24.items():
            if c < MIN_COUNT_24H or len(u24[t]) < MIN_USERS_24H:
                continue
            base = max(cbase[t] / nbase if nbase else 0.0, archive_rate(t), floor)
            lift = (c / n24) / base
            looks_addressed = " " not in t and t not in emotes_low and t not in meanings and first24[t] >= 0.5 * c
            if lift >= MIN_LIFT and ok_term(t) and not looks_addressed:
                cands.append((math.log(lift) * math.sqrt(len(u24[t])), t, lift))
        cands.sort(reverse=True)
        # A bigram only stays if it isn't just its two words trending on their own.
        uni = {t for _, t, _ in cands if " " not in t}
        cands = [x for x in cands if " " not in x[1] or not all(p in uni for p in x[1].split(" "))]
    trending = {t: lift for _, t, lift in cands[:MAX_TRENDING]}

    terms = state["terms"]
    for t in trending:
        e = terms.setdefault(t, {"first_seen": now.isoformat(timespec="minutes")})
        e["last_trending"] = now.isoformat(timespec="minutes")
    keep = {t for t, e in terms.items() if not e.get("held") and
            dt.datetime.fromisoformat(e.get("last_trending", e["first_seen"])) >= now - dt.timedelta(days=TRACK_DAYS)}

    # ---- context per term
    def co_terms(t):
        co = collections.Counter()
        for _, _, _, toks in recent:
            if t in toks:
                co.update(x for x in toks if x != t and " " not in x)
        tot = sum(1 for _, _, _, toks in recent if t in toks) or 1
        n7 = len(recent) or 1
        out = []
        for x, c in co.most_common(200):
            base = sum(1 for _, _, _, toks in recent if x in toks) if c >= 5 else 0
            if c >= 5 and base and ok_term(x) and x not in t.split(" "):
                out.append(((c / tot) / (base / n7), x))
        out.sort(reverse=True)
        return [emotes_low.get(x, x) for _, x in out[:6]]

    def quotes(t):
        senders = collections.defaultdict(set)
        for _, u, text, toks in recent:
            if t in toks:
                norm = " ".join(text.split())
                senders[norm].add(u)
        good = []
        for norm, us in senders.items():
            if len(us) < 3 or len(norm) > 120 or URLISH.search(norm) or LONGNUM.search(norm) or BLOCK.search(norm):
                continue
            words = TOK.findall(norm.lower())
            if any(h16(salt, w) in names for w in words if w not in emotes_low):
                continue
            adds = set(norm.lower().split()) - set(t.split(" "))
            good.append((len(us), bool(adds), norm))
        good.sort(key=lambda x: (x[1], x[0]), reverse=True)
        if any(g[1] for g in good):
            good = [g for g in good if g[1]] + [g for g in good if not g[1]][:1]
        return [{"text": q, "chatters": n} for n, _, q in good[:2]]

    def samples(t, k=25):
        out = []
        for _, _, text, toks in reversed(recent):
            if t in toks and not URLISH.search(text):
                s = " ".join("[user]" if (TOK.fullmatch(w.lower()) and h16(salt, w.lower()) in names and
                                          w.lower() not in emotes_low) else w for w in text.split())
                out.append(s[:200])
                if len(out) >= k:
                    break
        return out

    def archive_info(t):
        ys = rates.get(t)
        if not ys:
            return None, "not seen in 2014-2020 DGG chat"
        first = min(ys)
        peak = max(ys, key=ys.get)
        r19 = round(1e5 * ys.get("2019", 0.0), 1)
        return ({"first_year": first, "peak_year": peak, "rate_2019_per100k": r19},
                f"first seen {first}, peak {peak}, {r19} per 100k messages in 2019")

    days14 = [(now - dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    entries, calls, drafted, held_now = [], 0, [], []
    for t in sorted(keep, key=lambda x: (-trending.get(x, 0), -c24[x])):
        e = terms[t]
        kind = "emote" if t in emotes_low else ("phrase" if " " in t else "word")
        arch, arch_note = archive_info(t)
        info = {"kind": kind, "messages_24h": c24[t], "chatters_24h": len(u24[t]),
                "lift": round(trending.get(t, 0), 1), "archive_note": arch_note, "co": co_terms(t)}
        if t in meanings:
            e["definition"], e["source"] = meanings[t]
            e["def_date"] = e.get("def_date") or now.strftime("%Y-%m-%d")
        else:
            d = defs.get(t)
            if d and d.get("date") and (not e.get("definition") or d["date"] >= e.get("def_date", "")):
                if d.get("sensitive"):
                    e.update(held=True, held_reason=d.get("reason") or "flagged sensitive",
                             held_at=now.isoformat(timespec="minutes"))
                    held_now.append(t)
                    continue
                if d.get("definition"):
                    e.update(definition=str(d["definition"]).strip()[:400], source="Claude",
                             model=d.get("model", "Claude"), def_date=d["date"], kind=str(d.get("kind", kind))[:20])
            stale = (not e.get("definition") or (t in trending and e.get("source") == "Claude" and
                     dt.date.fromisoformat(e["def_date"]) <= now.date() - dt.timedelta(days=REDRAFT_DAYS)))
            if stale:
                pending.append({"term": emotes_low.get(t, t), "key": t, **info, "samples": samples(t)})
            if stale and calls < MAX_CALLS_PER_RUN:
                s = samples(t)
                if a.dry_run or not key:
                    drafted.append((t, info, len(s)))
                else:
                    calls += 1
                    try:
                        d = call_claude(key, t, info, s)
                    except (urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as err:
                        d = None
                        e["last_error"] = f"{now.isoformat(timespec='minutes')} {type(err).__name__}"
                    if d:
                        if d["sensitive"]:
                            e.update(held=True, held_reason=d["reason"] or "flagged sensitive",
                                     held_at=now.isoformat(timespec="minutes"))
                            held_now.append(t)
                            continue
                        e.update(definition=d["definition"], source="Claude", model=MODEL,
                                 def_date=now.strftime("%Y-%m-%d"), kind=d["kind"])
        if e.get("held"):
            continue
        entries.append({
            "term": emotes_low.get(t, t), "kind": e.get("kind") if e.get("source") == "Claude" else kind,
            "status": "trending" if t in trending else "ongoing",
            "definition": e.get("definition"), "definition_source": e.get("source"),
            "definition_date": e.get("def_date"),
            "messages_24h": c24[t], "chatters_24h": len(u24[t]),
            "per_10k_24h": round(1e4 * c24[t] / n24, 1) if n24 else 0, "lift": info["lift"],
            "trend": [{"day": d, "per_10k": round(1e4 * daily[d][t] / day_n[d], 1) if day_n[d] else None} for d in days14],
            "first_seen_live": e["first_seen"], "archive": arch, "co_terms": info["co"], "quotes": quotes(t),
        })

    # ---- every emote used in the last 7 days, with its meaning where one exists
    held_keys = {t for t, e in terms.items() if e.get("held")} | {k for k, v in defs.items() if v.get("sensitive")}
    ecount = collections.Counter()
    for _, _, _, toks in recent:
        ecount.update(x for x in toks if x in emotes_low)
    emote_rows = []
    for k, c in ecount.most_common():
        if k in held_keys or BLOCK.search(k):
            continue
        if k in meanings:
            mean, src = meanings[k]
        elif (defs.get(k) or {}).get("definition"):
            mean, src = defs[k]["definition"], "Claude"
        else:
            mean, src = None, None
        emote_rows.append({"emote": emotes_low[k], "messages_7d": c,
                           "share_7d": round(c / max(1, len(recent)), 4), "meaning": mean, "source": src})

    os.makedirs(a.out, exist_ok=True)
    payload = {"generated": now.isoformat(timespec="minutes"), "messages_24h": n24, "messages_7d": len(recent),
               "model": MODEL, "entries": entries, "emotes": emote_rows}
    with open(os.path.join(a.out, "glossary.json"), "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    with open(a.pending + ".tmp", "w") as f:
        json.dump({"generated": now.isoformat(timespec="minutes"), "terms": pending[:40]}, f, indent=1)
    os.replace(a.pending + ".tmp", a.pending)
    tmp = a.state + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, a.state)
    print(json.dumps({"entries": len(entries), "trending": len(trending), "api_calls": calls,
                      "held_now": held_now, "pending_drafts": [t for t, _, _ in drafted]}))


if __name__ == "__main__":
    main()
