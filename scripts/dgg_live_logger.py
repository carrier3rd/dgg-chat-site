#!/usr/bin/env python3
"""Live destiny.gg chat logger (read-only; approved by Cake, Nov 2 2026).

Connects anonymously to wss://chat.destiny.gg/ws (no token needed for reading; checked Nov 2 2026) and writes
every chat message to one JSON-lines file per UTC day. It never sends chat messages.

Privacy: nicks are hashed at ingest (HMAC-SHA256 with the local laptop salt, first 16 hex chars), the same
scheme as orl_aggregate.py and dgg_chat_pull.py, so live, archive and RustleSearch hashes line up.
Kept per message: ts (ms), u (hash), text, sub (subscription tier or null), flags (roles + features, e.g. bot,
moderator, used to drop bots later). Nothing else from the user object is stored.

Files in --out:
  YYYY-MM-DD.jsonl         today's messages (plain text while the day is open)
  YYYY-MM-DD.jsonl.gz      finished days, compressed at rollover
  sessions.jsonl           one line per connection: start, end, reason  -> gaps are the time between sessions
  daily_counts.json        per day: messages, and counts of other event types (JOIN, QUIT, MUTE, BAN, BROADCAST...)
  status.json              live status for the page in --status-dir

Run under systemd --user with Restart=always (see the unit text at the bottom of this file).
Needs: pip install websockets
"""
import argparse
import asyncio
import collections
import datetime as dt
import gzip
import hashlib
import hmac
import json
import os
import shutil
import signal
import sys
import time

try:
    import websockets
except ImportError:
    sys.exit("pip install websockets")

URL = "wss://chat.destiny.gg/ws"
HEADERS = {"Origin": "https://www.destiny.gg", "User-Agent": "socialscope-logger/0.1 (read-only research logger)"}


def utc_day(ms=None):
    t = dt.datetime.fromtimestamp((ms / 1000) if ms else time.time(), dt.timezone.utc)
    return t.strftime("%Y-%m-%d")


class Logger:
    def __init__(self, out, status_dir, salt):
        self.out, self.status_dir, self.salt = out, status_dir, salt
        os.makedirs(out, exist_ok=True)
        os.makedirs(status_dir, exist_ok=True)
        self.day = None
        self.fh = None
        self.seen = collections.deque(maxlen=20000)
        self.seen_set = set()
        self.counts = self._load_json(os.path.join(out, "daily_counts.json"), {})
        self.per_min = collections.Counter()  # minute epoch -> messages, last ~3 hours
        self.connected_since = None
        self.session_msgs = 0
        self.last_msg_ms = None
        self.last_status = 0
        self._compress_old_days()

    @staticmethod
    def _load_json(path, default):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default

    def _atomic_json(self, path, obj):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, path)

    def _compress_old_days(self):
        today = utc_day()
        for fn in os.listdir(self.out):
            if fn.endswith(".jsonl") and fn[:10] != today and fn[:4].isdigit():
                src = os.path.join(self.out, fn)
                with open(src, "rb") as a, gzip.open(src + ".gz", "ab") as b:
                    shutil.copyfileobj(a, b)
                os.remove(src)

    def _rollover(self, day):
        if self.fh:
            self.fh.close()
            self.fh = None
        self.day = day
        self.fh = open(os.path.join(self.out, f"{day}.jsonl"), "a", buffering=1)
        self._compress_old_days()

    def hash(self, nick):
        return hmac.new(self.salt, nick.lower().encode(), hashlib.sha256).hexdigest()[:16]

    def count(self, day, kind):
        d = self.counts.setdefault(day, {})
        d[kind] = d.get(kind, 0) + 1

    def msg(self, j):
        # "id" in a DGG MSG is the sender's account id, not a message id, so it can't be the dedup key.
        # A HISTORY replay repeats messages exactly, so (timestamp, nick, text) identifies a message.
        ts = j.get("timestamp") or int(time.time() * 1000)
        key = (ts, j.get("nick"), j.get("data"))
        if key in self.seen_set:
            return
        if len(self.seen) == self.seen.maxlen:
            self.seen_set.discard(self.seen[0])
        self.seen.append(key)
        self.seen_set.add(key)
        day = utc_day(ts)
        if day != self.day:
            self._rollover(day)
        sub = j.get("subscription")
        rec = {
            "ts": ts,
            "u": self.hash(j.get("nick") or ""),
            "text": j.get("data", ""),
            "sub": (sub or {}).get("tier") if isinstance(sub, dict) else sub,
            "flags": sorted(set((j.get("roles") or []) + (j.get("features") or []))),
        }
        self.fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.count(day, "MSG")
        self.per_min[ts // 60000] += 1
        self.session_msgs += 1
        self.last_msg_ms = ts

    def handle(self, raw):
        sp = raw.find(" ")
        kind, body = (raw[:sp], raw[sp + 1:]) if sp > 0 else (raw, "")
        if kind == "MSG":
            try:
                self.msg(json.loads(body))
            except json.JSONDecodeError:
                pass
        elif kind == "HISTORY":
            # Recent backlog sent on connect; fills short gaps. Entries are raw "MSG {...}" lines.
            try:
                for line in json.loads(body):
                    if isinstance(line, str) and line.startswith("MSG "):
                        self.handle(line)
            except Exception:
                pass
        else:
            self.count(utc_day(), kind)  # counts only; no nicks or reasons stored

    def status(self, force=False):
        now = time.time()
        if not force and now - self.last_status < 5:
            return
        self.last_status = now
        cutoff = int(now // 60) - 180
        for k in [k for k in self.per_min if k < cutoff]:
            del self.per_min[k]
        sessions = self._recent_sessions()
        self._atomic_json(os.path.join(self.status_dir, "status.json"), {
            "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "connected": self.connected_since is not None,
            "connected_since": self.connected_since,
            "today": utc_day(),
            "msgs_today": self.counts.get(utc_day(), {}).get("MSG", 0),
            "session_msgs": self.session_msgs,
            "last_msg": dt.datetime.fromtimestamp(self.last_msg_ms / 1000, dt.timezone.utc).isoformat(timespec="seconds")
            if self.last_msg_ms else None,
            "per_minute": [[k * 60, self.per_min.get(k, 0)] for k in range(cutoff, int(now // 60) + 1)],
            "days": {d: c.get("MSG", 0) for d, c in sorted(self.counts.items())[-14:]},
            "recent_sessions": sessions,
        })
        self._atomic_json(os.path.join(self.out, "daily_counts.json"), self.counts)

    def _recent_sessions(self):
        path = os.path.join(self.out, "sessions.jsonl")
        try:
            with open(path) as f:
                return [json.loads(l) for l in f.readlines()[-8:]]
        except Exception:
            return []

    def session_log(self, start, end, reason):
        with open(os.path.join(self.out, "sessions.jsonl"), "a") as f:
            f.write(json.dumps({"start": start, "end": end, "reason": reason}) + "\n")


async def run(lg):
    delay = 5
    while True:
        start = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        reason = "closed"
        try:
            # ping_interval=None: chat.destiny.gg does not answer websocket pings, so library keepalives closed
            # every connection after 60 s (Nov 2 2026). Real network drops still raise and reconnect below.
            try:  # websockets >= 14 uses additional_headers; older versions use extra_headers
                conn = websockets.connect(URL, additional_headers=HEADERS, ping_interval=None,
                                          max_size=2**22)
            except TypeError:
                conn = websockets.connect(URL, extra_headers=HEADERS, ping_interval=None,
                                          max_size=2**22)
            async with conn as ws:
                lg.connected_since = start
                lg.session_msgs = 0
                lg.status(force=True)
                delay = 5
                async for raw in ws:
                    lg.handle(raw if isinstance(raw, str) else raw.decode("utf-8", "replace"))
                    lg.status()
        except asyncio.CancelledError:
            reason = "stopped"
            raise
        except Exception as e:
            reason = type(e).__name__
        finally:
            end = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            if lg.connected_since:
                lg.session_log(lg.connected_since, end, reason)
            lg.connected_since = None
            lg.status(force=True)
        await asyncio.sleep(delay)
        delay = min(delay * 2, 300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/socialscope_data/dgg_live"))
    ap.add_argument("--status-dir", default=os.path.expanduser("~/socialscope_data/dgg_live_status"))
    ap.add_argument("--salt-file", required=True)
    args = ap.parse_args()
    with open(os.path.expanduser(args.salt_file)) as f:
        salt = f.read().strip().encode()
    lg = Logger(args.out, args.status_dir, salt)
    loop = asyncio.new_event_loop()
    task = loop.create_task(run(lg))
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, task.cancel)
    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        if lg.fh:
            lg.fh.close()
        lg.status(force=True)


if __name__ == "__main__":
    main()

# systemd --user unit (~/.config/systemd/user/dgg-live.service):
# [Unit]
# Description=destiny.gg read-only chat logger (socialscope)
# After=network-online.target
# [Service]
# ExecStart=/usr/bin/python3 /home/probs/socialscope/scripts/dgg_live_logger.py --salt-file /home/probs/socialscope/.socialscope_salt
# Restart=always
# RestartSec=10
# [Install]
# WantedBy=default.target
#
# then: systemctl --user daemon-reload && systemctl --user enable --now dgg-live && loginctl enable-linger $USER
