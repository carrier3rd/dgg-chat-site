#!/usr/bin/env python3
"""Where hostility toward streamers comes from, across the 23 archived chats (reads orl_deep.py output).

1. Home community: for each hashed account, the chat where it sent most of its archived messages, if it sent 20+
   messages in total and that chat holds at least half of them; otherwise "mixed" (or "light" under 20 messages).
   DGG (destiny.gg) and vaush.gg are site chats with their own accounts, so linking them to Twitch accounts only works
   for same-spelled names.
2. For every chat: hostile streamer-directed messages split by the sender's home community, and the per-message
   hostility rate of each home group present in that chat.
3. Hate-raid candidate days: one chat, one day, one outside home community sending 15+ hostile directed messages
   from 5+ accounts, at least 5x that community's usual daily level in that chat, with most senders new to the chat
   (first seen there within 7 days).

Outputs in <deep>/_cross/:
  homes_summary.tsv        home community, accounts
  hostility_by_origin.tsv  chat, origin, senders, hostile_directed, directed, messages, hostile_per_10k_msgs, share
  raid_candidates.tsv      chat, day, origin, hostile_directed, senders, new_sender_share, baseline_per_day, ratio
  chat_hostility.tsv       chat, messages, directed, hostile_directed, hostile_per_10k, days
"""
import argparse
import collections
import csv
import datetime as dt
import os

csv.field_size_limit(10**8)


def rows(p):
    with open(p, newline="") as f:
        yield from csv.DictReader(f, delimiter="\t")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", default=os.path.expanduser("~/socialscope_data/orl_deep"))
    a = ap.parse_args()
    chans = sorted(c for c in os.listdir(a.deep) if os.path.exists(os.path.join(a.deep, c, "DONE")))
    out = os.path.join(a.deep, "_cross")
    os.makedirs(out, exist_ok=True)

    # ---- home community
    per_user = collections.defaultdict(dict)
    first_day = {}
    for c in chans:
        for r in rows(os.path.join(a.deep, c, "users.tsv")):
            per_user[r["user_hash"]][c] = int(r["messages"])
            first_day[(c, r["user_hash"])] = r["first_day"]
    home = {}
    for u, d in per_user.items():
        tot = sum(d.values())
        top = max(d, key=d.get)
        home[u] = "light" if tot < 20 else (top if d[top] >= 0.5 * tot else "mixed")
    with open(os.path.join(out, "homes_summary.tsv"), "w") as f:
        f.write("home\taccounts\n")
        for h, n in collections.Counter(home.values()).most_common():
            f.write(f"{h}\t{n}\n")

    # ---- hostility by origin, per chat
    with open(os.path.join(out, "hostility_by_origin.tsv"), "w") as fo, \
            open(os.path.join(out, "raid_candidates.tsv"), "w") as fr, \
            open(os.path.join(out, "chat_hostility.tsv"), "w") as fc:
        fo.write("chat\torigin\tsenders\thostile_directed\tdirected\tmessages\thostile_per_10k_msgs\tshare_of_hostile\n")
        fr.write("chat\tday\torigin\thostile_directed\tsenders\tnew_sender_share\tbaseline_per_day\tratio\n")
        fc.write("chat\tmessages\tdirected\thostile_directed\thostile_per_10k\tdays\n")
        for c in chans:
            msgs = collections.Counter()
            hos = collections.Counter()
            dirs = collections.Counter()
            senders = collections.Counter()
            for r in rows(os.path.join(a.deep, c, "users.tsv")):
                h = home.get(r["user_hash"], "light")
                msgs[h] += int(r["messages"])
                dirs[h] += int(r["directed"])
                hos[h] += int(r["hostile_directed"])
                if int(r["hostile_directed"]):
                    senders[h] += 1
            total_h = sum(hos.values()) or 1
            for h in sorted(msgs, key=lambda x: -hos[x]):
                if msgs[h] < 1000 and not hos[h]:
                    continue
                label = "own chat" if h == c else h
                fo.write(f"{c}\t{label}\t{senders[h]}\t{hos[h]}\t{dirs[h]}\t{msgs[h]}\t"
                         f"{round(1e4 * hos[h] / msgs[h], 2) if msgs[h] else ''}\t{round(hos[h] / total_h, 4)}\n")
            daily = list(rows(os.path.join(a.deep, c, "daily.tsv")))
            n_days = len(daily) or 1
            tot_msgs = sum(int(d["messages"]) for d in daily)
            fc.write(f"{c}\t{tot_msgs}\t{sum(int(d['directed']) for d in daily)}\t"
                     f"{sum(int(d['hostile_directed']) for d in daily)}\t"
                     f"{round(1e4 * sum(int(d['hostile_directed']) for d in daily) / max(tot_msgs, 1), 2)}\t{len(daily)}\n")

            # raid candidates: outside origins only
            by_day = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
            for r in rows(os.path.join(a.deep, c, "hostile_days.tsv")):
                h = home.get(r["user_hash"], "light")
                if h in (c, "light", "mixed"):
                    continue
                rec = by_day[r["day"]][h]
                rec[0] += int(r["hostile_directed"])
                rec[1] += 1
                fd = first_day.get((c, r["user_hash"]), r["day"])
                if (dt.date.fromisoformat(r["day"]) - dt.date.fromisoformat(fd)).days <= 7:
                    rec[2] += 1
            base = collections.Counter()
            for d in by_day.values():
                for h, rec in d.items():
                    base[h] += rec[0]
            for day in sorted(by_day):
                for h, (hd, ns, new) in by_day[day].items():
                    bl = (base[h] - hd) / max(n_days - 1, 1)
                    ratio = hd / bl if bl > 0 else float("inf")
                    if hd >= 15 and ns >= 5 and ratio >= 5 and new / ns >= 0.5:
                        fr.write(f"{c}\t{day}\t{h}\t{hd}\t{ns}\t{round(new / ns, 2)}\t{round(bl, 2)}\t"
                                 f"{'inf' if ratio == float('inf') else round(ratio, 1)}\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
