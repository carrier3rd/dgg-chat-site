#!/usr/bin/env python3
"""Pull destiny.gg chat logs from the RustleSearch API, one file per UTC day.

Endpoint (found by watching rustlesearch.dev's own requests, Nov 2 2026):
  GET https://api-v2.rustlesearch.dev/anon/search
      ?channel=Destinygg&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD[&text=...][&search_after=<ms>]
  -> {"type", "error", "data": {"count", "countLimit", "messages": [
        {"channel", "text", "ts", "username", "searchAfter"}, ...]}}
  100 messages per page, newest first. Pass the last message's searchAfter to get the next page.
  Empty text returns every message for the day.

Usernames are hashed at ingest (HMAC-SHA256 with the project salt, first 16 hex chars).
No raw nick is ever written to disk.

Run on the laptop (this workspace cannot reach the API):
  nohup python3 scripts/dgg_chat_pull.py --salt-file ~/socialscope/.socialscope_salt &
  (or export SOCIALSCOPE_SALT and drop --salt-file)
Chat hashes never need to match Reddit hashes: chat accounts are not linked to Reddit accounts.

Resumable: finished days are skipped; a day is written to .partial and renamed when complete.
Nov 9 2026: the anonymous API allows 200 requests a day and one busy day needs ~500-700 pages, so a day could never
finish in one sitting and every restart began it again. Now (1) each page is appended to .partial as its own gzip
member and <day>.cursor records search_after, counts and the file size after that page, so a restart truncates to
the last good page and continues mid-day; (2) every API request is logged in <out>/_requests.json and, once
--daily-cap requests fall in the trailing 24 h, the pull sleeps until the oldest one ages out.
Progress lines go to ~/socialscope_data/STATUS.txt.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api-v2.rustlesearch.dev/anon/search"
EMOTES = "https://cdn.destiny.gg/emotes/emotes.json"
UA = "socialscope-research/0.1 (academic project; 1 req/s)"

# Same weeks as the Reddit pulls, plus the Oct 27 top-up week. Each runs 7 days from the start date.
WEEK_STARTS = ["2026-08-18", "2026-09-08", "2026-09-22", "2026-10-13", "2026-10-20", "2026-10-27"]

# Chat accounts flagged as bots/system. Flag only; analysis drops them. Extend after looking at top hashes.
KNOWN_BOTS = {"bot"}


def salted_hash(name: str, salt: bytes) -> str:
    return hmac.new(salt, name.lower().encode(), hashlib.sha256).hexdigest()[:16]


class Budget:
    """Keeps API requests under a trailing-24-hour cap; the request log survives restarts."""

    def __init__(self, path: str, cap: int):
        self.path, self.cap = path, cap
        try:
            self.times = json.load(open(path))
        except (OSError, ValueError):
            self.times = []

    def take(self):
        while True:
            now = time.time()
            self.times = [t for t in self.times if t > now - 86400]
            if len(self.times) < self.cap:
                break
            wake = self.times[0] + 86400 + 5
            status(f"daily cap {self.cap} reached; sleeping until "
                   f"{dt.datetime.fromtimestamp(wake).strftime('%a %H:%M')}")
            time.sleep(max(1.0, wake - now))
        self.times.append(time.time())
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.times, f)
        os.replace(tmp, self.path)


BUDGET = None  # set in main(); counts every request to the search API, retries included


def get_json(url: str, tries: int = 6):
    delay = 5
    for attempt in range(tries):
        if BUDGET is not None and url.startswith(API):
            BUDGET.take()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                wait = int(e.headers.get("Retry-After") or delay)
                time.sleep(wait)
                delay = min(delay * 2, 300)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 300)
                continue
            raise


def status(line: str):
    path = os.path.expanduser("~/socialscope_data/STATUS.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(path, "a") as f:
        f.write(f"[{stamp}] dgg_chat: {line}\n")


class Progress:
    """Writes progress.json (no usernames, no message text) for the live progress page.

    Within a day, pages come newest first, so the share of the day already covered is
    (end of day - oldest timestamp so far) / 24 h. That gives a real per-day bar without knowing
    the message count in advance.
    """

    def __init__(self, path: str, days: list):
        self.path = path
        self.started = time.time()
        self.days = [{"day": d, "state": "pending", "msgs": 0, "frac": 0.0} for d in days]
        self.active_secs = 0.0  # time spent on days pulled this run (skipped days excluded from ETA)
        self.active_frac = 0.0
        self.note = ""

    def _write(self):
        done = sum(1 for d in self.days if d["state"] == "done")
        overall = sum(1.0 if d["state"] in ("done", "skipped") else d["frac"] for d in self.days) / len(self.days)
        eta = None
        if self.active_frac > 0.05:
            remaining = sum(1.0 - d["frac"] for d in self.days if d["state"] in ("pending", "running"))
            eta = self.active_secs / self.active_frac * remaining
        payload = {
            "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "started": dt.datetime.fromtimestamp(self.started, dt.timezone.utc).isoformat(timespec="seconds"),
            "overall": round(overall, 4),
            "days_done": done,
            "days_total": len(self.days),
            "msgs_total": sum(d["msgs"] for d in self.days),
            "eta_seconds": round(eta) if eta is not None else None,
            "note": self.note,
            "days": self.days,
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, self.path)

    def update(self, i: int, **kw):
        self.days[i].update(kw)
        self._write()

    def add_active(self, secs: float, frac: float):
        self.active_secs += secs
        self.active_frac += frac


def pull_day(day: str, out_dir: str, salt: bytes, pause: float, prog: "Progress" = None, idx: int = 0):
    final = os.path.join(out_dir, f"{day}.jsonl.gz")
    if os.path.exists(final):
        return None
    day_end = dt.datetime.fromisoformat(day + "T00:00:00+00:00") + dt.timedelta(days=1)
    t_last, frac_last = time.time(), 0.0
    partial = final + ".partial"
    cursor_path = os.path.join(out_dir, f"{day}.cursor")
    base = {"channel": "Destinygg", "start_date": day, "end_date": day}
    search_after, n, pages, ties, size = None, 0, 0, 0, 0
    if os.path.exists(cursor_path) and os.path.exists(partial):  # resume mid-day after the last complete page
        c = json.load(open(cursor_path))
        search_after, n, pages, ties, size = c["search_after"], c["n"], c["pages"], c["ties"], c["size"]
        os.truncate(partial, size)
        frac_last = c.get("frac", 0.0)
        if prog is not None:
            prog.update(idx, state="running", msgs=n, frac=round(frac_last, 4))
    else:
        open(partial, "wb").close()
    with open(partial, "ab") as fb:
        while True:
            q = dict(base)
            if search_after is not None:
                q["search_after"] = search_after
            j = get_json(API + "?" + urllib.parse.urlencode(q))
            if j.get("error"):
                raise RuntimeError(f"{day}: API error {j.get('error')}")
            msgs = j["data"]["messages"]
            if not msgs:
                break
            lines = []
            for m in msgs:
                user = m.get("username") or ""
                lines.append(json.dumps({
                    "ts": m["ts"],
                    "u": salted_hash(user, salt),
                    "bot": user.lower() in KNOWN_BOTS,
                    "text": m.get("text", ""),
                }, ensure_ascii=False) + "\n")
            fb.write(gzip.compress("".join(lines).encode("utf-8")))
            fb.flush()
            os.fsync(fb.fileno())
            size = fb.tell()
            n += len(msgs)
            pages += 1
            # searchAfter is a ms timestamp; messages sharing the boundary ms can be skipped. Count how often.
            if len(msgs) > 1 and msgs[-1]["searchAfter"] == msgs[-2]["searchAfter"]:
                ties += 1
            if prog is not None:
                oldest = dt.datetime.fromisoformat(msgs[-1]["ts"].replace("Z", "+00:00"))
                frac = min(max((day_end - oldest).total_seconds() / 86400, 0.0), 0.999)
                now = time.time()
                prog.add_active(now - t_last, frac - frac_last)
                t_last, frac_last = now, frac
                prog.update(idx, state="running", msgs=n, frac=round(frac, 4))
            nxt = msgs[-1]["searchAfter"]
            if nxt == search_after or len(msgs) < 100:
                break
            search_after = nxt
            tmp = cursor_path + ".tmp"
            with open(tmp, "w") as cf:
                json.dump({"search_after": search_after, "n": n, "pages": pages, "ties": ties, "size": size,
                           "frac": frac_last}, cf)
            os.replace(tmp, cursor_path)
            time.sleep(pause)
    os.replace(partial, final)
    if os.path.exists(cursor_path):
        os.remove(cursor_path)
    if prog is not None:
        prog.add_active(time.time() - t_last, 1.0 - frac_last)
        prog.update(idx, state="done", msgs=n, frac=1.0)
    return n, pages, ties


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/socialscope_data/dgg_chat"))
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--daily-cap", type=int, default=190,
                    help="max search requests in any 24 h (RustleSearch allows 200 anonymous; 10 kept spare)")
    ap.add_argument("--days", nargs="*", help="explicit YYYY-MM-DD days (default: the six Reddit weeks)")
    ap.add_argument("--salt-file", help="read the hashing salt from this file instead of SOCIALSCOPE_SALT")
    ap.add_argument("--progress-dir", default=os.path.expanduser("~/socialscope_data/dgg_progress"),
                    help="where progress.json goes; serve this folder (and only this one) for the progress page")
    args = ap.parse_args()

    if args.salt_file:
        with open(os.path.expanduser(args.salt_file)) as f:
            salt = f.read().strip()
    else:
        salt = os.environ.get("SOCIALSCOPE_SALT", "")
    if not salt:
        sys.exit("No salt: pass --salt-file or set SOCIALSCOPE_SALT.")
    salt = salt.encode()
    os.makedirs(args.out, exist_ok=True)
    global BUDGET
    BUDGET = Budget(os.path.join(args.out, "_requests.json"), args.daily_cap)

    emotes_path = os.path.join(args.out, "emotes.json")
    if not os.path.exists(emotes_path):
        emotes = get_json(EMOTES)
        with open(emotes_path, "w") as f:
            json.dump([{"prefix": e["prefix"], "twitch": e.get("twitch"),
                        "minimumSubTier": e.get("minimumSubTier")} for e in emotes], f, indent=1)
        status(f"saved {len(emotes)} emotes")

    days = args.days or [
        (dt.date.fromisoformat(s) + dt.timedelta(d)).isoformat() for s in WEEK_STARTS for d in range(7)
    ]
    status(f"start: {len(days)} days -> {args.out}")
    os.makedirs(args.progress_dir, exist_ok=True)
    prog = Progress(os.path.join(args.progress_dir, "progress.json"), days)
    total = 0
    for i, day in enumerate(days, 1):
        t0 = time.time()
        try:
            res = pull_day(day, args.out, salt, args.pause, prog, i - 1)
        except Exception as e:
            prog.note = f"stopped on {day}: {type(e).__name__}"
            prog.update(i - 1, state="error")
            raise
        if res is None:
            prog.update(i - 1, state="skipped", frac=1.0)
            continue
        n, pages, ties = res
        total += n
        status(f"{day} done ({i}/{len(days)}): {n} msgs, {pages} pages, {ties} tie pages, "
               f"{(time.time() - t0) / 60:.1f} min; running total {total}")
    prog.note = "finished"
    prog._write()
    status(f"finished: {total} msgs")


if __name__ == "__main__":
    main()
