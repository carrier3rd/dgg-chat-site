#!/usr/bin/env python3
"""Build the public site's data files from the archive tables and the live DGG log.

Everything written here is public. Only aggregates leave this script: counts, shares, rates, emote names and
glossary terms. No message text, no nicks, no user hashes. Free-text "top words" are deliberately not published
(the live log has no nick list to filter them against); tracked vocabulary comes from data/glossary.csv instead.

Inputs (defaults are the laptop's paths):
  --agg       ~/socialscope_data/orl_agg          archive count tables (orl_aggregate.py output)
  --live      ~/socialscope_data/dgg_live         live log (dgg_live_logger.py output)
  --status    ~/socialscope_data/dgg_live_status/status.json
  --emotes    ~/socialscope_data/dgg_chat/emotes.json
  --glossary  ~/socialscope/data/glossary.csv
Output: --out <site>/data/*.json  (overwritten each run)
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import json
import os
import re
import statistics

csv.field_size_limit(10**8)
H = os.path.expanduser
DAYFILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl(\.gz)?$")  # skips *.broken-dedup.jsonl and other side files
TOK = re.compile(r"[A-Za-z0-9_']+")

# Archive channels: display name, chat platform, group. Groups are descriptive labels for the page.
CHANNELS = {
    "Destinygg": ("DGG (destiny.gg)", "site", "Destiny"),
    "Destiny": ("Destiny (Twitch)", "twitch", "Destiny"),
    "Denims": ("Denims", "twitch", "Orbit"),
    "Mindwavestv": ("Mindwave", "twitch", "Orbit"),
    "Melina": ("Melina", "twitch", "Orbit"),
    "Kelly_jean": ("Kelly Jean", "twitch", "Orbit"),
    "Invadervie": ("InvaderVie", "twitch", "Orbit"),
    "Rajjpatel": ("Rajj Patel", "twitch", "Orbit"),
    "Badbunny": ("Badbunny", "twitch", "Orbit"),
    "Hasanabi": ("Hasan", "twitch", "Political"),
    "Vaushvidya": ("Vaush (Twitch)", "twitch", "Political"),
    "Vaushgg": ("Vaush (vaush.gg)", "site", "Political"),
    "Hutch": ("Hutch", "twitch", "Political"),
    "Nickjfuentes": ("Nick Fuentes", "twitch", "Political"),
    "Asmongold": ("Asmongold", "twitch", "Variety"),
    "Athenelive": ("Athene", "twitch", "Variety"),
    "H3h3productions": ("H3", "twitch", "Variety"),
    "Moistcr1tikal": ("Moist", "twitch", "Variety"),
    "Ludwig": ("Ludwig", "twitch", "Variety"),
    "Pokimane": ("Pokimane", "twitch", "Variety"),
    "Trainwreckstv": ("Trainwreck", "twitch", "Variety"),
    "Reckful": ("Reckful", "twitch", "Variety"),
    "Trihex": ("Trihex", "twitch", "Variety"),
}
ELECTORAL = set("trump biden bernie sanders warren obama hillary clinton election vote voting democrat democrats "
                "republican republicans gop liberal liberals conservative conservatives maga".split())
CULTURE = set("sjw sjws feminist feminists feminism snowflake snowflakes woke dei gamergate politicallycorrect "
              "diversity tranny cuck cucks soy soyboy incel".split())
POLITICS_CHANNELS = ["Asmongold", "Destiny", "Destinygg", "Hasanabi", "Hutch", "Badbunny", "Vaushgg", "Ludwig",
                     "Moistcr1tikal", "Pokimane"]


def rows(path, delim=","):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f, delimiter=delim)


def dump(out, name, obj):
    with open(os.path.join(out, name), "w") as f:
        json.dump(obj, f, separators=(",", ":"))


def median_from_hist(hist):
    n = sum(hist.values())
    acc = 0
    for k in sorted(hist):
        acc += hist[k]
        if acc >= n / 2:
            return k
    return None


# ---------------------------------------------------------------- archive

def build_archive(agg, out, emotes):
    present = [c for c in CHANNELS if os.path.exists(os.path.join(agg, c, "DONE"))]
    regs = {}
    for c in present:
        d = collections.defaultdict(set)
        for r in rows(os.path.join(agg, c, "user_months.tsv"), "\t"):
            if int(r["messages"]) >= 3:
                d[r["month"]].add(r["user_hash"])
        regs[c] = d

    def overlap(a, b):
        x = n = 0
        for mo, s in regs[a].items():
            if mo in regs[b] and len(s) >= 30 and len(regs[b][mo]) >= 500:
                x += len(s & regs[b][mo])
                n += len(s)
        return round(100 * x / n, 1) if n else None

    chans, ov = [], []
    for c in present:
        name, plat, group = CHANNELS[c]
        months = list(rows(os.path.join(agg, c, "monthly.csv")))
        total = sum(int(r["messages"]) for r in months)
        busy = [r["month"] for r in months if int(r["messages"]) >= 1000] or [months[0]["month"]]
        hist = collections.Counter()
        for r in rows(os.path.join(agg, c, "lengths.csv")):
            hist[int(r["words"])] += int(r["messages"])
        shorts = collections.Counter()
        for r in rows(os.path.join(agg, c, "short_msgs.tsv"), "\t"):
            shorts[r["message"]] += int(r["count"])
        top = next((m for m, _ in shorts.most_common(20) if not m.isdigit() and len(m) > 1), "")
        chans.append({"key": c, "channel": name, "platform": plat, "group": group, "messages": total,
                      "first_month": busy[0], "last_month": busy[-1], "median_words": median_from_hist(hist),
                      "top_short_message": top})
        if c not in ("Destiny", "Destinygg"):
            ov.append({"key": c, "channel": name, "platform": plat, "group": group,
                       "pct_in_destiny_twitch": overlap(c, "Destiny") if "Destiny" in regs else None,
                       "pct_in_dgg": overlap(c, "Destinygg") if "Destinygg" in regs else None})
    dump(out, "archive_channels.json", chans)
    dump(out, "archive_overlap.json", ov)

    if "Destinygg" in present:
        yr = collections.defaultdict(lambda: [0, 0, 0])
        for r in rows(os.path.join(agg, "Destinygg", "monthly.csv")):
            y = r["month"][:4]
            yr[y][0] += int(r["messages"])
            yr[y][1] += 1
            yr[y][2] = max(yr[y][2], int(r["chatters"]))
        dump(out, "archive_dgg_years.json", [{"year": y, "messages": v[0], "messages_per_month": v[0] // v[1],
                                              "peak_monthly_chatters": v[2], "months": v[1]}
                                             for y, v in sorted(yr.items()) if v[1] >= 3])
        tok = collections.defaultdict(collections.Counter)
        for r in rows(os.path.join(agg, "Destinygg", "tokens.tsv"), "\t"):
            if r["token"] in emotes:
                tok[r["year"]][r["token"]] += int(r["count"])
        dump(out, "archive_dgg_emotes.json", [{"year": y, "top5": [k for k, _ in t.most_common(5)],
                                               "PEPE": t["PEPE"], "YEE": t["YEE"]}
                                              for y, t in sorted(tok.items()) if sum(t.values()) > 10000])

    pol = []
    for c in POLITICS_CHANNELS:
        if c not in present:
            continue
        n = collections.Counter()
        for r in rows(os.path.join(agg, c, "monthly.csv")):
            n[r["month"][:4]] += int(r["messages"])
        e = collections.Counter()
        w = collections.Counter()
        for r in rows(os.path.join(agg, c, "tokens.tsv"), "\t"):
            t = r["token"].lower()
            if t in ELECTORAL:
                e[r["year"]] += int(r["count"])
            elif t in CULTURE:
                w[r["year"]] += int(r["count"])
        for y in sorted(n):
            if n[y] >= 50000:
                pol.append({"key": c, "channel": CHANNELS[c][0], "year": y,
                            "electoral_per_10k": round(1e4 * e[y] / n[y], 1),
                            "culture_war_per_10k": round(1e4 * w[y] / n[y], 1)})
    dump(out, "archive_politics.json", pol)

    def monthly_vs_destiny(c, min_regs):
        out_rows = []
        for mo, s in sorted(regs[c].items()):
            d = regs.get("Destiny", {}).get(mo)
            if d and len(s) >= min_regs:
                i = len(s & d)
                out_rows.append({"month": mo, "regulars": len(s), "destiny_regulars": len(d), "shared": i,
                                 "pct_of_channel": round(100 * i / len(s), 1),
                                 "pct_of_destiny": round(100 * i / len(d), 1)})
        return out_rows

    for c, fname, m in [("Hasanabi", "archive_hasan_monthly.json", 300),
                        ("Badbunny", "archive_badbunny_monthly.json", 500),
                        ("Nickjfuentes", "archive_fuentes_monthly.json", 30),
                        ("Asmongold", "archive_asmongold_monthly.json", 5000)]:
        if c in present and "Destiny" in present:
            dump(out, fname, monthly_vs_destiny(c, m))
    return sum(r["messages"] for r in chans), len(chans)


# ---------------------------------------------------------------- live

def build_live(live, status_path, out, emotes, terms):
    days = sorted(m.group(1) for fn in os.listdir(live) if (m := DAYFILE.match(fn)))
    days = sorted(set(days))
    emotes_low = {e.lower() for e in emotes}
    terms = {t for t in terms if t not in emotes_low}  # emotes have their own chart
    single = {t for t in terms if " " not in t}
    multi = {t: re.compile(r"\b" + re.escape(t) + r"\b") for t in terms if " " in t}
    now = dt.datetime.now(dt.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    cutoff7 = (now - dt.timedelta(days=7)).timestamp() * 1000

    day_rows, hours = [], collections.Counter()
    emo7, term7, n7 = collections.Counter(), collections.Counter(), 0
    for d in days:
        msgs = users = emote_only = 0
        first_ts = None
        hist = collections.Counter()
        seen_u = set()
        for suffix in (".jsonl.gz", ".jsonl"):
            p = os.path.join(live, d + suffix)
            if not os.path.exists(p):
                continue
            op = gzip.open if suffix.endswith(".gz") else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if "bot" in (r.get("flags") or []):
                        continue
                    text = r.get("text") or ""
                    words = text.split()
                    msgs += 1
                    first_ts = r["ts"] if first_ts is None else min(first_ts, r["ts"])
                    seen_u.add(r.get("u"))
                    hist[min(len(words), 100)] += 1
                    em = [w for w in words if w in emotes]
                    if words and len(em) == len(words):
                        emote_only += 1
                    if r["ts"] >= cutoff7:
                        n7 += 1
                        hours[int(r["ts"] // 3600000) * 3600] += 1
                        emo7.update(set(em))
                        low = text.lower()
                        toks = set(TOK.findall(low))
                        term7.update(toks & single)
                        term7.update(t for t, rx in multi.items() if rx.search(low))
        users = len(seen_u)
        day_rows.append({"day": d, "messages": msgs, "chatters": users,
                         "emote_only_share": round(emote_only / msgs, 4) if msgs else None,
                         "median_words": median_from_hist(hist) if msgs else None,
                         "partial": d == today, "_first": first_ts})

    # Connected minutes per day, from the session log plus the open connection.
    spans = []
    sp = os.path.join(live, "sessions.jsonl")
    if os.path.exists(sp):
        for line in open(sp):
            try:
                s = json.loads(line)
                spans.append((dt.datetime.fromisoformat(s["start"]), dt.datetime.fromisoformat(s["end"])))
            except Exception:
                pass
    try:
        st = json.load(open(status_path))
        if st.get("connected") and st.get("connected_since"):
            spans.append((dt.datetime.fromisoformat(st["connected_since"]), dt.datetime.fromisoformat(st["updated"])))
    except Exception:
        st = {}
    for row in day_rows:
        d0 = dt.datetime.fromisoformat(row["day"] + "T00:00:00+00:00")
        d1 = d0 + dt.timedelta(days=1)
        first = row.pop("_first")
        if first:  # coverage counts only from the day's first logged message (skips discarded stretches)
            d0 = max(d0, dt.datetime.fromtimestamp(first / 1000 - 60, dt.timezone.utc))
        d1 = min(d1, now)
        mins = sum(max(0, (min(b, d1) - max(a, d0)).total_seconds()) for a, b in spans) / 60
        row["connected_minutes"] = round(min(mins, 1440))

    start = int((now - dt.timedelta(days=7)).timestamp() // 3600) * 3600
    end = int(now.timestamp() // 3600) * 3600
    hour_rows = [{"hour": dt.datetime.fromtimestamp(h, dt.timezone.utc).isoformat(timespec="minutes"),
                  "messages": hours.get(h, 0)} for h in range(start, end + 1, 3600)]
    emote_rows = [{"emote": e, "messages": c, "share": round(c / n7, 4)} for e, c in emo7.most_common(20)] if n7 else []
    term_rows = [{"term": t, "messages": c, "per_10k": round(1e4 * c / n7, 1)}
                 for t, c in term7.most_common(25) if c >= 5] if n7 else []
    dump(out, "live_days.json", day_rows)
    dump(out, "live_hours.json", hour_rows)
    dump(out, "live_emotes.json", emote_rows)
    dump(out, "live_terms.json", term_rows)
    return {"live_first_day": days[0] if days else None, "live_messages": sum(r["messages"] for r in day_rows),
            "live_messages_7d": n7, "logger_connected": bool(st.get("connected")),
            "last_message": st.get("last_msg")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agg", default=H("~/socialscope_data/orl_agg"))
    ap.add_argument("--live", default=H("~/socialscope_data/dgg_live"))
    ap.add_argument("--status", default=H("~/socialscope_data/dgg_live_status/status.json"))
    ap.add_argument("--emotes", default=H("~/socialscope_data/dgg_chat/emotes.json"))
    ap.add_argument("--glossary", default=H("~/socialscope/data/glossary.csv"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-archive", action="store_true", help="rebuild only the live files (archive never changes)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    emotes = {e["prefix"] for e in json.load(open(a.emotes))}
    terms = {r["term"].strip().lower() for r in rows(a.glossary) if r.get("term")}
    meta = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}
    if not a.skip_archive or not os.path.exists(os.path.join(a.out, "archive_channels.json")):
        meta["archive_messages"], meta["archive_channels"] = build_archive(a.agg, a.out, emotes)
    else:
        old = json.load(open(os.path.join(a.out, "meta.json"))) if os.path.exists(os.path.join(a.out, "meta.json")) else {}
        meta["archive_messages"], meta["archive_channels"] = old.get("archive_messages"), old.get("archive_channels")
    meta.update(build_live(a.live, a.status, a.out, emotes, terms))
    dump(a.out, "meta.json", meta)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
