#!/usr/bin/env python3
"""Second pass over the OverRustle archive: event timeline, hostility toward streamers, effort-post language.

Reads each <Channel>.7z again (daily logs only), in date order, one channel at a time, and writes to
<out>/<Channel>/:
  daily.tsv            day, messages, chatters, new_chatters, emote_only, effort_posts, directed, hostile_directed
  bursts.tsv           day, rank, term, messages, chatters, lift, bigram   (top 15 bursting words per day vs the
                       previous 28 days; chatter names, links, digits and slurs removed)
  users.tsv            user_hash, first_day, last_day, active_days, messages, directed, hostile_directed, effort_posts
  hostile_days.tsv     day, user_hash, hostile_directed, directed, messages   (only account-days with hostility)
  ling_year.tsv        year, scope (all = 10% random sample | effort | directed), then ling.Acc summary columns
  effort_terms.tsv     year, term, count                (words in effort posts, names removed; for topics)
  samples_effort.jsonl     up to 120 effort posts per year, names replaced with [user]   (PRIVATE, never publish)
  samples_hostile.jsonl    up to 300 hostile streamer-directed messages, names replaced   (PRIVATE, for hand-checking)
  DONE

Privacy: nicks are hashed at ingest with the project salt (same scheme as orl_aggregate.py). Samples keep message
text with every word that matches a chatter's name replaced by [user]; they stay on this machine for validation only.

Usage (laptop):
  python3 -I scripts/orl_deep.py --archive "$HOME/Downloads/OverrustleLogs Archive" \
      --out ~/socialscope_data/orl_deep --salt-file ~/socialscope/.socialscope_salt \
      --emotes ~/socialscope_data/dgg_chat/emotes.json \
      --keep-file ~/socialscope/data/chat_keep_terms.txt ~/socialscope/socialscope/vocab.txt \
      --progress-dir ~/socialscope_data/orl_progress
Resumable: a channel with <out>/<Channel>/DONE is skipped.
"""
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import hmac
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ (ling.py, vader/)
import ling  # noqa: E402

try:
    from vader.vaderSentiment import SentimentIntensityAnalyzer  # scripts/vader
    VADER = SentimentIntensityAnalyzer()
except Exception:  # VADER is optional; effort-post sentiment is left blank without it
    VADER = None

LINE = re.compile(r"^\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?: UTC)?\] ([^:\s]+): (.*)$")
DAYFILE = re.compile(r"(^|/)(?:chatlog-)?(\d{4}-\d{2}-\d{2})\.txt(\.gz)?$")
TOK = re.compile(r"[a-z0-9_']+")
EFFORT_WORDS = 25
BASE_DAYS = 28

# Names chat uses for each streamer (lower case). A message naming one of these counts as directed at the streamer.
ALIASES = {
    "Destinygg": "destiny steven tiny stevie", "Destiny": "destiny steven tiny stevie",
    "Hasanabi": "hasan hasanabi piker hassan", "Vaushvidya": "vaush", "Vaushgg": "vaush",
    "Hutch": "hutch hutchinson", "Asmongold": "asmon asmongold zack zach", "Badbunny": "badbunny bunny",
    "Ludwig": "ludwig lud ahgren", "Moistcr1tikal": "charlie moist critikal cr1tikal", "H3h3productions": "ethan hila",
    "Pokimane": "poki pokimane imane", "Trainwreckstv": "trainwreck train tyler", "Reckful": "reckful byron",
    "Trihex": "trihex", "Athenelive": "athene", "Melina": "melina", "Mindwavestv": "mindwave", "Denims": "denims",
    "Kelly_jean": "kelly", "Invadervie": "vie invadervie invader", "Rajjpatel": "rajj", "Nickjfuentes": "fuentes nick",
}
STOP = set("""a about after again all also am an and any are as at be because been before being but by can could
did do does doing don't dont down for from get got had has have he her here him his how i i'm im if in into is it
it's its just know like lol me more my no not now of off oh on one only or our out really so some than that that's
thats the their them then there they this to too up us was we were what when where which who why will with would
you your yes yeah""".split())
WHITELIST = set()  # glossary terms that survive the name filter (from --keep-file)


def nickhash(salt, cache, nick):
    h = cache.get(nick)
    if h is None:
        h = hmac.new(salt, nick.lower().encode(), hashlib.sha256).hexdigest()[:16]
        if len(cache) < 2_000_000:
            cache[nick] = h
    return h


def list_dayfiles(archive):
    out = subprocess.run(["7z", "l", "-ba", "-slt", archive], capture_output=True, text=True, check=True).stdout
    sizes, cur = {}, None
    for line in out.splitlines():
        if line.startswith("Path = "):
            cur = line[7:]
        elif line.startswith("Size = ") and cur is not None:
            sizes[cur] = int(line[7:] or 0)
            cur = None
    by_date = {}
    for p, s in sizes.items():
        m = DAYFILE.search(p.replace("\\", "/"))
        if m and (m.group(2) not in by_date or s > sizes[by_date[m.group(2)]]):
            by_date[m.group(2)] = p
    return [(d, by_date[d], sizes[by_date[d]]) for d in sorted(by_date)]


def write_progress(path, state):
    state["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(path + ".tmp", "w") as f:
        json.dump(state, f)
    os.replace(path + ".tmp", path)


def scrub(text, nicks):
    return " ".join("[user]" if w.lower().strip("@:,.!?") in nicks else w for w in text.split())


def process_channel(archive, channel, out_dir, salt, emotes, prog, prog_path, idx, rng):
    cdir = os.path.join(out_dir, channel)
    os.makedirs(cdir, exist_ok=True)
    if os.path.exists(os.path.join(cdir, "DONE")):
        prog["items"][idx].update(state="skipped", frac=1.0)
        write_progress(prog_path, prog)
        return
    item = prog["items"][idx]
    item.update(state="listing")
    write_progress(prog_path, prog)
    days = list_dayfiles(archive)
    if not days:
        item.update(state="error", note="no daily log files")
        write_progress(prog_path, prog)
        return
    total_bytes = sum(s for _, _, s in days) or 1
    aliases = set(ALIASES.get(channel, channel.lower()).split())
    emotes_low = {e.lower() for e in emotes}

    tmp = tempfile.mkdtemp(prefix=f"orldeep_{channel}_", dir=os.path.expanduser("~/socialscope_data"))
    try:
        item.update(state="extracting", note=f"{len(days)} days")
        write_progress(prog_path, prog)
        lst = os.path.join(tmp, "_files.txt")
        with open(lst, "w") as f:
            f.write("\n".join(p for _, p, _ in days) + "\n")
        subprocess.run(["7z", "x", "-y", "-bso0", "-bsp0", f"-o{tmp}", archive, f"@{lst}"], check=True)

        cache, nicks = {}, set()                 # nicks: lower-case raw names, in memory only
        users = {}                               # hash -> [first, last, active_days, msgs, directed, hostile, effort]
        last_seen_day = {}
        base = collections.Counter()             # word counts over the previous BASE_DAYS days
        base_days = collections.deque()          # (msgs, Counter) per day
        base_msgs = 0
        bursts_raw = []                          # (day, term, count, chatters, lift, bigram)
        daily_rows, hostile_rows = [], []
        ling_acc = collections.defaultdict(ling.Acc)
        effort_terms = collections.defaultdict(collections.Counter)
        eff_samples = collections.defaultdict(list)
        eff_seen = collections.Counter()
        host_samples, host_seen = [], 0
        done_bytes, msgs_total, t0 = 0, 0, time.time()

        for n_day, (day, rel, size) in enumerate(days, 1):
            path = os.path.join(tmp, rel)
            if not os.path.exists(path):
                continue
            year = day[:4]
            opener = gzip.open if path.endswith(".gz") else open
            day_counts = collections.Counter()
            day_pairs = set()
            day_bigrams = collections.Counter()
            day_users = set()
            day_user_stats = collections.defaultdict(lambda: [0, 0, 0])   # msgs, directed, hostile
            n_msgs = new_ch = emote_only = n_effort = n_dir = n_host = 0
            with opener(path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = LINE.match(line.rstrip("\n"))
                    if not m:
                        continue
                    nick, text = m.group(7), m.group(8)
                    nl = nick.lower()
                    nicks.add(nl)
                    u = nickhash(salt, cache, nick)
                    n_msgs += 1
                    if u not in users:
                        users[u] = [day, day, 0, 0, 0, 0, 0]
                        new_ch += 1
                    rec = users[u]
                    rec[1] = day
                    if last_seen_day.get(u) != day:
                        rec[2] += 1
                        last_seen_day[u] = day
                    rec[3] += 1
                    day_users.add(u)
                    dus = day_user_stats[u]
                    dus[0] += 1

                    words = text.split()
                    if words and all(w in emotes for w in words):
                        emote_only += 1
                    low = TOK.findall(ling.LINK.sub(" ", text).lower())
                    uniq = set(low)
                    day_counts.update(uniq)
                    for t in uniq:
                        day_pairs.add((t, u))
                    for a, b in zip(low, low[1:]):
                        if a not in STOP and b not in STOP:
                            day_bigrams[a + " " + b] += 1

                    # Directed at the streamer: names them, or says "you" without opening with a chatter's name.
                    first = words[0].lower().strip("@:,") if words else ""
                    to_chatter = text.startswith("@") or (first in nicks and first not in aliases)
                    directed = bool(uniq & aliases) or (bool(uniq & ling.SECOND) and not to_chatter)
                    long_enough = len(words) >= EFFORT_WORDS
                    sampled = rng.random() < 0.10   # the "all messages" baseline uses a 10% random sample
                    f = ling.features(text, emotes) if (directed or long_enough or sampled) else None
                    if directed:
                        n_dir += 1
                        rec[4] += 1
                        dus[1] += 1
                        ling_acc[(year, "directed")].add(f)
                        if ling.is_hostile(text, low):
                            n_host += 1
                            rec[5] += 1
                            dus[2] += 1
                            host_seen += 1
                            if len(host_samples) < 300:
                                host_samples.append((day, text))
                            elif rng.random() < 300 / host_seen:
                                host_samples[rng.randrange(300)] = (day, text)
                    if sampled:
                        ling_acc[(year, "all")].add(f)
                    if long_enough and f["words"] >= EFFORT_WORDS:
                        n_effort += 1
                        rec[6] += 1
                        v = VADER.polarity_scores(text)["compound"] if VADER else None
                        ling_acc[(year, "effort")].add(f, v)
                        effort_terms[year].update(t for t in low if t not in STOP and len(t) > 2 and not t.isdigit())
                        eff_seen[year] += 1
                        s = eff_samples[year]
                        if len(s) < 120:
                            s.append(text)
                        elif rng.random() < 120 / eff_seen[year]:
                            s[rng.randrange(120)] = text
            os.remove(path)
            msgs_total += n_msgs

            # Bursts: today's rate against the previous 28 days.
            if n_msgs >= 200 and base_msgs >= 2000:
                users_per = collections.Counter(t for t, _ in day_pairs)
                cands = []
                for t, c in day_counts.items():
                    if c < 25 or users_per[t] < 8 or len(t) < 3 or t.isdigit() or t in STOP:
                        continue
                    lift = (c / n_msgs) / ((base[t] + 1) / (base_msgs + 1000))
                    if lift >= 4:
                        cands.append((math.log(lift) * math.sqrt(users_per[t]), t, c, users_per[t], lift))
                cands.sort(reverse=True)
                top_bi = [b for b, _ in day_bigrams.most_common(2000)]
                for _, t, c, uc, lift in cands[:60]:
                    big = next((b for b in top_bi if t in b.split(" ")), "")
                    bursts_raw.append((day, t, c, uc, round(lift, 1), big))
            base.update(day_counts)
            base_msgs += n_msgs
            base_days.append((n_msgs, day_counts))
            if len(base_days) > BASE_DAYS:
                old_n, old_c = base_days.popleft()
                base.subtract(old_c)
                base_msgs -= old_n
                base += collections.Counter()  # drop zero and negative entries

            daily_rows.append((day, n_msgs, len(day_users), new_ch, emote_only, n_effort, n_dir, n_host))
            for u, (m_, d_, h_) in day_user_stats.items():
                if h_:
                    hostile_rows.append((day, u, h_, d_, m_))

            done_bytes += size
            if n_day % 10 == 0 or n_day == len(days):
                frac = done_bytes / total_bytes
                el = time.time() - t0
                item.update(state="running", frac=round(frac, 4), msgs=msgs_total, note=day,
                            eta_seconds=round(el / frac * (1 - frac)) if frac > 0.02 else None)
                write_progress(prog_path, prog)

        # ---- write outputs (name filter uses the full nick list for this channel)
        def term_ok(t):
            return (t in WHITELIST or t in emotes_low or t not in nicks) and not ling.SLUR.search(t) \
                and not ling.LINK.search(t)

        def bigram_ok(b):
            return all(term_ok(p) for p in b.split(" "))

        with open(os.path.join(cdir, "daily.tsv"), "w") as fo:
            fo.write("day\tmessages\tchatters\tnew_chatters\temote_only\teffort_posts\tdirected\thostile_directed\n")
            for r in daily_rows:
                fo.write("\t".join(map(str, r)) + "\n")
        with open(os.path.join(cdir, "bursts.tsv"), "w") as fo:
            fo.write("day\trank\tterm\tmessages\tchatters\tlift\tbigram\n")
            rank = collections.Counter()
            for day, t, c, uc, lift, big in bursts_raw:
                if term_ok(t) and rank[day] < 15:
                    rank[day] += 1
                    fo.write(f"{day}\t{rank[day]}\t{t}\t{c}\t{uc}\t{lift}\t{big if bigram_ok(big) else ''}\n")
        with open(os.path.join(cdir, "users.tsv"), "w") as fo:
            fo.write("user_hash\tfirst_day\tlast_day\tactive_days\tmessages\tdirected\thostile_directed\teffort_posts\n")
            for u, r in users.items():
                fo.write(u + "\t" + "\t".join(map(str, r)) + "\n")
        with open(os.path.join(cdir, "hostile_days.tsv"), "w") as fo:
            fo.write("day\tuser_hash\thostile_directed\tdirected\tmessages\n")
            for r in hostile_rows:
                fo.write("\t".join(map(str, r)) + "\n")
        keys = None
        with open(os.path.join(cdir, "ling_year.tsv"), "w") as fo:
            for (y, scope), acc in sorted(ling_acc.items()):
                s = acc.summary()
                if keys is None:
                    keys = list(s)
                    fo.write("year\tscope\t" + "\t".join(keys) + "\n")
                fo.write(f"{y}\t{scope}\t" + "\t".join("" if s[k] is None else str(s[k]) for k in keys) + "\n")
        with open(os.path.join(cdir, "effort_terms.tsv"), "w") as fo:
            fo.write("year\tterm\tcount\n")
            for y in sorted(effort_terms):
                for t, c in effort_terms[y].most_common(3000):
                    if c >= 3 and term_ok(t):
                        fo.write(f"{y}\t{t}\t{c}\n")
        with open(os.path.join(cdir, "samples_effort.jsonl"), "w") as fo:
            for y in sorted(eff_samples):
                for t in eff_samples[y]:
                    fo.write(json.dumps({"year": y, "text": scrub(t, nicks - aliases)}, ensure_ascii=False) + "\n")
        with open(os.path.join(cdir, "samples_hostile.jsonl"), "w") as fo:
            for d, t in sorted(host_samples):
                fo.write(json.dumps({"day": d, "text": scrub(t, nicks - aliases)}, ensure_ascii=False) + "\n")
        with open(os.path.join(cdir, "DONE"), "w") as fo:
            fo.write(f"{msgs_total} messages, {len(days)} days, {dt.datetime.now().isoformat(timespec='seconds')}\n")
        item.update(state="done", frac=1.0, msgs=msgs_total, note=f"{len(days)} days", eta_seconds=None)
        write_progress(prog_path, prog)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--out", default=os.path.expanduser("~/socialscope_data/orl_deep"))
    ap.add_argument("--salt-file", required=True)
    ap.add_argument("--emotes", required=True)
    ap.add_argument("--keep-file", nargs="*", default=[],
                    help="word lists (one term per line: glossary terms, an English vocabulary) whose words survive "
                         "the chatter-name filter")
    ap.add_argument("--progress-dir", default=os.path.expanduser("~/socialscope_data/orl_progress"))
    ap.add_argument("--channels", nargs="*")
    args = ap.parse_args()
    if not shutil.which("7z"):
        sys.exit("7z not found")
    salt = open(os.path.expanduser(args.salt_file)).read().strip().encode()
    emotes = {e["prefix"] for e in json.load(open(os.path.expanduser(args.emotes)))}
    for kf in args.keep_file:
        if os.path.exists(os.path.expanduser(kf)):
            WHITELIST.update(t.strip().lower() for t in open(os.path.expanduser(kf)) if t.strip() and " " not in t)
    if VADER is None:
        print("note: VADER not importable; effort-post sentiment will be blank", file=sys.stderr)
    files = sorted((fn for fn in os.listdir(args.archive) if fn.endswith(".7z")),
                   key=lambda fn: os.path.getsize(os.path.join(args.archive, fn)))
    chans = [fn[:-3] for fn in files if not args.channels or fn[:-3] in args.channels]
    os.makedirs(args.progress_dir, exist_ok=True)
    prog_path = os.path.join(args.progress_dir, "progress.json")
    prog = {"title": "Archive deep pass (timeline, hostility, language)",
            "items": [{"label": c, "state": "pending", "frac": 0.0, "msgs": 0, "note": "",
                       "mb": round(os.path.getsize(os.path.join(args.archive, c + ".7z")) / 1e6)} for c in chans]}
    write_progress(prog_path, prog)
    rng = random.Random(20261103)
    for i, c in enumerate(chans):
        try:
            process_channel(os.path.join(args.archive, c + ".7z"), c, args.out, salt, emotes, prog, prog_path, i, rng)
        except Exception as e:
            prog["items"][i].update(state="error", note=f"{type(e).__name__}: {str(e)[:80]}")
            write_progress(prog_path, prog)
            print(f"{c}: {e!r}", file=sys.stderr)
    prog["note"] = "finished"
    write_progress(prog_path, prog)


if __name__ == "__main__":
    main()
