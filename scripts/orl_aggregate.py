#!/usr/bin/env python3
"""Aggregate OverRustle archive channels into privacy-safe count tables.

For each <Channel>.7z in the archive folder:
  1. 7z lists the archive; only daily channel logs (YYYY-MM-DD.txt[.gz]) are used. Per-user log files
     duplicate those lines and are skipped.
  2. The daily logs are extracted to a temp dir, parsed, and the temp dir is deleted.
  3. Nicks are hashed (HMAC-SHA256, local salt). Raw nicks never reach the output.

Outputs, in <out>/<channel>/ (no raw nicks, no full message text except short repeated messages):
  listing.txt          top-level structure of the archive (directory names that look like dates or logs only)
  monthly.csv          month, messages, chatters, cmd_msgs (lines starting with "!")
  lengths.csv          year, words, messages          (message length histogram)
  tokens.tsv           year, token, count             (count >= 5; tokens that equal any chat nick are dropped,
                                                       except emotes and the whitelist below)
  short_msgs.tsv       year, message, count           (messages of <= 3 tokens seen >= 5 times; for emote-only
                                                       shares and combos; same nick filter applied per token)
  user_years.tsv       year, user_hash, messages
  user_months.tsv      month, user_hash, messages     (for aggregate cross-channel overlap only)

Usage (laptop; needs the 7z CLI: sudo apt install p7zip-full):
  python3 scripts/orl_aggregate.py --archive "$HOME/Downloads/OverrustleLogs Archive" \
      --out ~/socialscope_data/orl_agg --salt-file ~/socialscope/.socialscope_salt \
      --emotes ~/socialscope_data/dgg_chat/emotes.json \
      --progress-dir ~/socialscope_data/orl_progress
Resumable: a channel with <out>/<channel>/DONE is skipped.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

LINE = re.compile(r"^\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?: UTC)?\] ([^:\s]+): (.*)$")
DAYFILE = re.compile(r"(^|/)(?:chatlog-)?(\d{4}-\d{2}-\d{2})\.txt(\.gz)?$")
TOKEN = re.compile(r"[A-Za-z0-9_']+")
# Kept even when a chat nick has the same spelling: streamer and community names the glossary needs.
WHITELIST = {
    "destiny", "dgg", "hutch", "asmongold", "asmon", "ludwig", "melina", "denims", "h3", "ethan", "hila",
    "moist", "critikal", "charlie", "fuentes", "nick", "badbunny", "mindwave", "hasan", "pepe", "yee",
}


def salted_hash(name, salt):
    return hmac.new(salt, name.lower().encode(), hashlib.sha256).hexdigest()[:16]


def write_progress(path, state):
    if not path:
        return
    state["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def list_dayfiles(archive):
    out = subprocess.run(["7z", "l", "-ba", "-slt", archive], capture_output=True, text=True, check=True).stdout
    paths, sizes, cur = [], {}, None
    for line in out.splitlines():
        if line.startswith("Path = "):
            cur = line[7:]
        elif line.startswith("Size = ") and cur is not None:
            sizes[cur] = int(line[7:] or 0)
            paths.append(cur)
            cur = None
    days = [p for p in paths if DAYFILE.search(p.replace("\\", "/"))]
    # Structure summary: count files under each top two path components, naming only date-like dirs.
    struct = collections.Counter()
    for p in paths:
        parts = p.replace("\\", "/").split("/")
        shown = [x if re.search(r"(chatlog|\d{4})", x, re.I) else "<other>" for x in parts[:2]]
        struct["/".join(shown)] += 1
    return days, sizes, struct


def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def process_channel(archive, channel, out_dir, salt, emotes, prog, prog_path, idx):
    cdir = os.path.join(out_dir, channel)
    os.makedirs(cdir, exist_ok=True)
    if os.path.exists(os.path.join(cdir, "DONE")):
        prog["items"][idx].update(state="skipped", frac=1.0)
        write_progress(prog_path, prog)
        return

    prog["items"][idx].update(state="listing")
    write_progress(prog_path, prog)
    days, sizes, struct = list_dayfiles(archive)
    with open(os.path.join(cdir, "listing.txt"), "w") as f:
        f.write(f"daily log files: {len(days)}\n")
        for k, v in struct.most_common(40):
            f.write(f"{v}\t{k}\n")
    if not days:
        prog["items"][idx].update(state="error", note="no daily log files found")
        write_progress(prog_path, prog)
        return
    # Several channel-folder variants can hold the same date; keep the largest file per date.
    by_date = {}
    for p in days:
        d = DAYFILE.search(p.replace("\\", "/")).group(2)
        if d not in by_date or sizes.get(p, 0) > sizes.get(by_date[d], 0):
            by_date[d] = p
    chosen = [by_date[d] for d in sorted(by_date)]
    total_bytes = sum(sizes.get(p, 0) for p in chosen) or 1

    tmp = tempfile.mkdtemp(prefix=f"orl_{channel}_", dir=os.path.expanduser("~/socialscope_data"))
    try:
        prog["items"][idx].update(state="extracting", note=f"{len(chosen)} days")
        write_progress(prog_path, prog)
        listfile = os.path.join(tmp, "_files.txt")
        with open(listfile, "w") as f:
            f.write("\n".join(chosen) + "\n")
        subprocess.run(["7z", "x", "-y", "-bso0", "-bsp0", f"-o{tmp}", archive, f"@{listfile}"], check=True)

        monthly = collections.defaultdict(lambda: [0, set(), 0])
        lengths = collections.Counter()
        tokens = collections.defaultdict(collections.Counter)
        shorts = collections.defaultdict(collections.Counter)
        user_years = collections.Counter()
        user_months = collections.Counter()
        nicks = set()
        done_bytes, msgs, t0 = 0, 0, time.time()

        for n, rel in enumerate(chosen, 1):
            path = os.path.join(tmp, rel)
            if not os.path.exists(path):
                continue
            with open_text(path) as f:
                for line in f:
                    m = LINE.match(line.rstrip("\n"))
                    if not m:
                        continue
                    y, mo, nick, text = m.group(1), m.group(2), m.group(7), m.group(8)
                    month = f"{y}-{mo}"
                    u = salted_hash(nick, salt)
                    nicks.add(nick.lower())
                    rec = monthly[month]
                    rec[0] += 1
                    rec[1].add(u)
                    if text.startswith("!"):
                        rec[2] += 1
                    toks = TOKEN.findall(text)
                    lengths[(y, min(len(toks), 100))] += 1
                    tokens[y].update(toks)
                    if 0 < len(toks) <= 3:
                        shorts[y][" ".join(toks)] += 1
                    user_years[(y, u)] += 1
                    user_months[(month, u)] += 1
                    msgs += 1
            done_bytes += sizes.get(rel, 0)
            os.remove(path)
            if n % 20 == 0 or n == len(chosen):
                frac = done_bytes / total_bytes
                el = time.time() - t0
                prog["items"][idx].update(state="running", frac=round(frac, 4), msgs=msgs,
                                          note=rel.replace("\\", "/").split("/")[-1][:10],
                                          eta_seconds=round(el / frac * (1 - frac)) if frac > 0.02 else None)
                write_progress(prog_path, prog)

        def keep(tok):
            t = tok.lower()
            return t not in nicks or tok in emotes or t in WHITELIST

        with open(os.path.join(cdir, "monthly.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["month", "messages", "chatters", "cmd_msgs"])
            for month in sorted(monthly):
                r = monthly[month]
                w.writerow([month, r[0], len(r[1]), r[2]])
        with open(os.path.join(cdir, "lengths.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["year", "words", "messages"])
            for (y, k), v in sorted(lengths.items()):
                w.writerow([y, k, v])
        with open(os.path.join(cdir, "tokens.tsv"), "w") as f:
            f.write("year\ttoken\tcount\n")
            for y in sorted(tokens):
                for tok, c in tokens[y].most_common():
                    if c < 5:
                        break
                    if keep(tok):
                        f.write(f"{y}\t{tok}\t{c}\n")
        with open(os.path.join(cdir, "short_msgs.tsv"), "w") as f:
            f.write("year\tmessage\tcount\n")
            for y in sorted(shorts):
                for msg, c in shorts[y].most_common():
                    if c < 5:
                        break
                    if all(keep(t) for t in msg.split(" ")):
                        f.write(f"{y}\t{msg}\t{c}\n")
        with open(os.path.join(cdir, "user_years.tsv"), "w") as f:
            f.write("year\tuser_hash\tmessages\n")
            for (y, u), c in sorted(user_years.items()):
                f.write(f"{y}\t{u}\t{c}\n")
        with open(os.path.join(cdir, "user_months.tsv"), "w") as f:
            f.write("month\tuser_hash\tmessages\n")
            for (mo, u), c in sorted(user_months.items()):
                f.write(f"{mo}\t{u}\t{c}\n")
        with open(os.path.join(cdir, "DONE"), "w") as f:
            f.write(f"{msgs} messages, {len(chosen)} days, {dt.datetime.now().isoformat(timespec='seconds')}\n")
        prog["items"][idx].update(state="done", frac=1.0, msgs=msgs, note=f"{len(chosen)} days", eta_seconds=None)
        write_progress(prog_path, prog)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True, help="folder holding the <Channel>.7z files")
    ap.add_argument("--out", default=os.path.expanduser("~/socialscope_data/orl_agg"))
    ap.add_argument("--salt-file", required=True)
    ap.add_argument("--emotes", help="destiny.gg emotes.json; emote names survive the nick filter")
    ap.add_argument("--progress-dir", default=os.path.expanduser("~/socialscope_data/orl_progress"))
    ap.add_argument("--channels", nargs="*", help="subset of channel names (default: all .7z files, smallest first)")
    args = ap.parse_args()

    if not shutil.which("7z"):
        sys.exit("7z not found: sudo apt install p7zip-full")
    with open(os.path.expanduser(args.salt_file)) as f:
        salt = f.read().strip().encode()
    emotes = set()
    if args.emotes and os.path.exists(os.path.expanduser(args.emotes)):
        emotes = {e["prefix"] for e in json.load(open(os.path.expanduser(args.emotes)))}

    files = sorted((fn for fn in os.listdir(args.archive) if fn.endswith(".7z")),
                   key=lambda fn: os.path.getsize(os.path.join(args.archive, fn)))
    chans = [fn[:-3] for fn in files]
    if args.channels:
        chans = [c for c in chans if c in args.channels]
    os.makedirs(args.progress_dir, exist_ok=True)
    prog_path = os.path.join(args.progress_dir, "progress.json")
    prog = {"title": "OverRustle archive aggregation", "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "items": [{"label": c, "state": "pending", "frac": 0.0, "msgs": 0, "note": "",
                       "mb": round(os.path.getsize(os.path.join(args.archive, c + ".7z")) / 1e6)} for c in chans]}
    write_progress(prog_path, prog)
    for i, c in enumerate(chans):
        try:
            process_channel(os.path.join(args.archive, c + ".7z"), c, args.out, salt, emotes, prog, prog_path, i)
        except Exception as e:
            prog["items"][i].update(state="error", note=type(e).__name__)
            write_progress(prog_path, prog)
            print(f"{c}: {e!r}", file=sys.stderr)
    prog["note"] = "finished"
    write_progress(prog_path, prog)


if __name__ == "__main__":
    main()
