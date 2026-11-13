"""Links to state media and known state-run proxy sites.

    from socialscope import sources
    sources.state_media("pulls/*.zip", out_dir="sources")

Writes state_media.csv (one row per link: outlet, country, kind, sub, hashed account, score, text) and
state_media.md (counts by outlet, sub, and how many accounts post 2+ such links). A link is not proof of
anything: people link RT to mock it. Read the rows before drawing conclusions.

The domain list starts from the US State Department GEC report "Pillars of Russia's Disinformation and
Propaganda Ecosystem" (Aug 2020), plus well-known state outlets. Ukrainska Pravda (pravda.com.ua) is a
Ukrainian outlet and is deliberately not matched. Extend DOMAINS as new networks are documented.
"""
import csv, glob, hashlib, json, os, re, zipfile
from collections import Counter

# (domain regex, outlet, country, kind)  kind: state = openly state-run, proxy = state-linked but hides it
DOMAINS = [
    (r"rt\.com|rt\.rs|actualidad\.rt\.com|francais\.rt\.com", "RT", "Russia", "state"),
    (r"sputniknews\.[a-z.]+|sputnikglobe\.com|sputniknews\.com", "Sputnik", "Russia", "state"),
    (r"tass\.com|tass\.ru", "TASS", "Russia", "state"),
    (r"ria\.ru", "RIA Novosti", "Russia", "state"),
    (r"ruptly\.tv", "Ruptly", "Russia", "state"),
    (r"redfish\.media", "Redfish", "Russia", "state"),
    (r"globalresearch\.ca", "Global Research", "Russia", "proxy"),
    (r"strategic-culture\.(?:org|su)", "Strategic Culture Foundation", "Russia", "proxy"),
    (r"journal-neo\.(?:org|su)", "New Eastern Outlook", "Russia", "proxy"),
    (r"news-front\.[a-z]+", "News Front", "Russia", "proxy"),
    (r"southfront\.(?:org|press)", "SouthFront", "Russia", "proxy"),
    (r"katehon\.com", "Katehon", "Russia", "proxy"),
    (r"geopolitica\.ru", "Geopolitica.ru", "Russia", "proxy"),
    (r"inforos\.ru", "InfoRos", "Russia", "proxy"),
    (r"pravda-[a-z]{2}\.com|news-pravda\.com", "Pravda network", "Russia", "proxy"),
    (r"cgtn\.com", "CGTN", "China", "state"),
    (r"globaltimes\.cn", "Global Times", "China", "state"),
    (r"presstv\.ir", "Press TV", "Iran", "state"),
]
_RX = [(re.compile(r"https?://(?:[a-z0-9-]+\.)*?(?:" + d + r")(?=[/\s)\]?#]|$)", re.I), o, c, k) for d, o, c, k in DOMAINS]


def _rows(inputs):
    for p in ([inputs] if isinstance(inputs, str) else inputs):
        for f in sorted(glob.glob(p)) or [p]:
            z = zipfile.ZipFile(f) if f.endswith(".zip") else None
            fh = z.open(z.namelist()[0]) if z else open(f, "rb")
            with fh:
                for line in fh:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue


def find(text):
    """Outlets linked in a piece of text: list of (outlet, country, kind)."""
    return [(o, c, k) for rx, o, c, k in _RX if rx.search(text or "")]


def state_media(inputs, out_dir="sources", salt=None):
    from . import salt as _salt
    salt = _salt.get(salt)
    rows, n = [], 0
    for r in _rows(inputs):
        n += 1
        text = " ".join(str(r.get(k) or "") for k in ("title", "selftext", "body", "url"))
        for o, c, k in find(text):
            rows.append({"outlet": o, "country": c, "kind": k, "sub": r.get("subreddit"),
                         "account": "acct_" + hashlib.sha256((salt + str(r.get("author"))).encode()).hexdigest()[:10],
                         "item": ("t3_" if "title" in r else "t1_") + str(r.get("id")), "created": int(float(r.get("created_utc") or 0)),
                         "score": r.get("score") or 0, "text": " ".join(text.split())[:300]})
    os.makedirs(out_dir, exist_ok=True)
    keys = ["outlet", "country", "kind", "sub", "account", "item", "created", "score", "text"]
    with open(os.path.join(out_dir, "state_media.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    acc = Counter(x["account"] for x in rows)
    md = ["# State media links", "", f"{len(rows)} links in {n:,} items.", ""]
    if rows:
        md += ["| Outlet | Kind | Links |", "|---|---|---|"] + \
              [f"| {o} | {k} | {c} |" for (o, k), c in Counter((x["outlet"], x["kind"]) for x in rows).most_common()]
        md += ["", "By sub: " + ", ".join(f"{s} {c}" for s, c in Counter(x["sub"] for x in rows).most_common()),
               f"Accounts posting 2+ such links: {sum(c >= 2 for c in acc.values())} of {len(acc)}."]
    open(os.path.join(out_dir, "state_media.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    return os.path.join(out_dir, "state_media.csv")
