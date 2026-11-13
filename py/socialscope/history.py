"""Stage 2: score full Reddit histories, compare shortlist against controls and known bots.

    from socialscope import history
    history.score(["histories/users_posts.zip", "histories/users_comments.zip"],
                  groups="shortlist/groups.csv", context="context/context_posts.zip", out_dir="history_scores")

Each account gets flags from rules fixed in advance (RULES below). The comparison table shows how often
each flag fires in each group. A flag only means something if it fires far more often for known bots
than for controls; the control column is the false-alarm rate.

Outputs: accounts.csv (hashed names unless reveal="known"), comparison.md, flagged_shortlist.csv
(shortlist accounts with 2+ flags, hashed unless reveal="all", for review).
"""
import csv, glob, hashlib, json, os, re, zipfile
from collections import Counter, defaultdict
from statistics import median

from . import signals

RULES = {
    "dormant_then_burst": "silent 180+ days, then 20+ items within 30 days",
    "metronome": "30+ items and posting-interval CV under 0.5",
    "rapid_fire": "30+ items and 20%+ of gaps under 60 seconds",
    "farm_subs": "20%+ of activity in karma-farming subs",
    "self_repeat": "10+ comments and 20%+ verbatim repeats of its own text",
    "ai_style": "5+ comments and 30%+ match the AI-quip template",
    "fast_replies": "10+ comments with thread context and 50%+ posted within 10 minutes of the thread",
    "topic_hopper": "20+ subs and no sub over 10% of activity",
    # v2, frozen Oct 28 2026 from the Oct 6-12 known bots; first fair test is the Oct 13-19 accounts
    "reply_window": "8+ comments with thread context and median reply 5-15 minutes after the thread was posted",
    "tourist": "first item within 6 months of the check, 60 or fewer items, 10+ subs, subreddit spread 0.95+",
    "hit_and_run": "10+ threads, 5% or fewer revisited, 55%+ of comments top-level",
    "uniform_length": "10+ comments, median 25+ words, word-count CV 0.85 or lower",
    # v3, frozen Oct 29 2026 from round 2 (exploratory there); first fair test is the Oct 20-26 accounts
    "young_account": "earliest item in the pulled history is under 90 days before the check date",
    # v3b, frozen Oct 29 2026 for the bot-rich round; needs pull_user_histories(oldest=True)
    "young_account_true": "account's oldest post or comment ever is under 90 days before the check date",
    # v4, frozen Oct 29 2026 from an older Reddit bot-spotting guide; first test is the bot-rich round
    "stock_name": "username looks like Word_Word#### or FirstnameLastname#### (Reddit's suggested-name style)",
    "gibberish_name": "username is 8+ lowercase letters (optional final digit) with no common 4+ letter word inside",
    "escaped_text": "any 2024-or-later title or comment containing a literal &amp; &gt; or &lt; (revised before data: Arctic Shift's 2023 text is stored escaped)",
    "quoted_comments": "5+ comments and 30%+ are entirely a > quote",
    "mash_comment": "any comment that is one 6+ letter token, 7+ distinct-run letters, 5+ different letters, 20% or fewer vowels, and mostly home/bottom row or 5+ consonants in a row (revised before data: the word-list version fired for 53% of round 2 controls)",
    "scam_domain": "any link to a .live, .life or .shop site",
    "posts_only": "3+ posts and no comments",
    # v5, frozen Oct 29 2026 from a 2026 vendor guide on evading mod detection; thresholds set on round 2 controls
    "ai_vocab": "10+ comments and 10%+ contain an AI-tic word or phrase (delve, tapestry, furthermore...) or an em dash",
    "md_structure": "10+ comments and 10%+ have a markdown header, a bold line on its own, or 2+ bullet lines",
    "flat_sentences": "5+ comments of 3+ sentences, median sentence-length CV 0.3 or lower",
    # v6, added Oct 29 2026, secondary: from the GEC "Pillars" report domain list (sources.DOMAINS)
    "state_media_link": "2+ links to state media or state-linked proxy sites (RT, Sputnik, Global Research, SouthFront...)",
    # v6, frozen Oct 29 2026 from the EEAS, VIGINUM, Taiwan NSB, Meta and OpenAI reports; secondary; first test bot-rich
    "political_pivot": "20+ items; first 70% of history 5% or less political, last 30% at least 30% political (warm-up then politics)",
    "sub_shift": "a 180+ day silence with 10+ items on each side and no subreddit in common before and after (resold or hijacked account)",
    "low_engagement": "30+ comments, median score 1 or less and 90th-percentile score 2 or less (volume without organic reach)",
    "batch_id": "Reddit account ID within 5,000 of another account in the same pool (accounts created in one batch)",
}
V3 = ("young_account", "young_account_true")
V5 = ("ai_vocab", "md_structure", "flat_sentences", "state_media_link")
V6 = ("political_pivot", "sub_shift", "low_engagement", "batch_id")
POLSUB = {"politics", "worldnews", "news", "conservative", "politicalcompassmemes", "destiny", "hasan_piker", "ukraine",
          "israelpalestine", "palestine", "israel", "neoliberal", "thebulwark", "samharris", "dsa", "tankiethedeprogram",
          "socialism", "republican", "democrats", "progressive", "geopolitics", "europe", "anime_titties", "politicalhumor",
          "askaliberal", "askconservatives", "moderatepolitics", "uspolitics", "thedavidpakmanshow", "enoughtrumpspam",
          "trump", "conspiracy", "ukrainianconflict", "russia"}
POL_RE = re.compile(r"\b(trump|biden|kamala|harris|maga|democrat\w*|republican\w*|gop|israel\w*|gaza|palestin\w*|hamas|idf|"
                    r"zionis\w*|ukrain\w*|russia\w*|putin|zelensk\w*|nato|election|vote[sd]?|voting|immigra\w*|ice|"
                    r"deport\w*|genocide|fascis\w*|communis\w*|socialis\w*|liberal\w*|leftist\w*|conservative\w*)\b", re.I)


def _political(r):
    return str(r.get("subreddit") or "").lower() in POLSUB or bool(POL_RE.search((r.get("body") or "") + " " + (r.get("title") or "")))
# Secondary rules (v4 + v5) never flag an account by themselves; they only add weight to an account a primary rule
# already flagged. Primary = the rules that have passed a fair test or are under test as main signals.
PRIMARY = ("young_account", "young_account_true", "posts_only", "tourist")
# v7 scoring (frozen Oct 29 2026 after the bot-rich round, for the next fresh round). Rules that held up across
# rounds 2, 3 and bot-rich flag an account (PRIMARY); rules with some lift support it (SUPPORT); the rest are still
# computed and reported but carry no weight (RETIRED). WEIGHTS come from a logistic regression on 472 labelled bots
# and 799 controls across the three rounds; held out one round at a time, the score catches 38-64% of bots at
# 2-3% false alarms. Account age carries most of the weight.
SUPPORT = ("fast_replies", "reply_window", "rapid_fire", "low_engagement", "uniform_length", "hit_and_run", "stock_name")
RETIRED = ("farm_subs", "self_repeat", "ai_style", "metronome", "topic_hopper", "dormant_then_burst", "gibberish_name",
           "escaped_text", "quoted_comments", "mash_comment", "scam_domain", "md_structure", "flat_sentences",
           "political_pivot", "sub_shift", "batch_id", "state_media_link", "ai_vocab")
WEIGHTS = {"_intercept": -2.62, "young_account": 4.30, "young_account_true": 0.0, "posts_only": 1.89, "tourist": 1.80,
           "rapid_fire": 1.34, "low_engagement": 1.15, "uniform_length": 1.13, "hit_and_run": 1.02, "stock_name": 0.58,
           "reply_window": 1.65, "fast_replies": 1.65}   # v7.1: fitted on round 3 + bot-rich with thread context, other weights held fixed
AI_RE = re.compile(r"\b(delve|delves|delving|tapestry|nuanced?|landscape|realm|multifaceted|pivotal|garner|bolster|"
                   r"commendable|testament|underscores?|intricate|navigate|navigating|fostering|foster|crucial|seamless|"
                   r"paramount|leverage|furthermore|moreover|additionally|ultimately|in conclusion|it's important to|"
                   r"it is important to|it's worth noting|boils down to|resonate|resonates|elevate|vibrant|meticulous|"
                   r"embark|showcase|showcasing)\b|\u2014", re.I)
MD_RE = re.compile(r"(?m)^\s{0,3}(#{1,6}\s|\*\*[^*\n]{2,60}\*\*\s*$)")
BUL_RE = re.compile(r"(?m)^\s*([-*\u2022]|\d+[.)])\s+\S")
SENT_RE = re.compile(r"[^.!?\n]+[.!?]+")
V4 = ("stock_name", "gibberish_name", "escaped_text", "quoted_comments", "mash_comment", "scam_domain", "posts_only")
_VOCAB = None


def _vocab():
    """Words used by 8+ different people in a week of the six subs (vocab.txt); stands in for a dictionary."""
    global _VOCAB
    if _VOCAB is None:
        p = os.path.join(os.path.dirname(__file__), "vocab.txt")
        _VOCAB = {w for w in open(p).read().split() if len(w) >= 4} if os.path.exists(p) else set()
    return _VOCAB


def _no_word(s):
    v = _vocab()
    return bool(v) and not any(s[i:i + L] in v for L in range(4, len(s) + 1) for i in range(len(s) - L + 1))


ROWS = ("asdfghjkl", "zxcvbnm")


def _mash(b):
    """Keyboard mash like 'klsjdfshdf': one token, few vowels, many different letters, mostly home/bottom row.
    Stretched words and laughter (hahaha, booooring) fail the distinct-letter and vowel tests."""
    t = b.strip().lower()
    if not re.fullmatch(r"[a-z]{6,}", t):
        return False
    c = re.sub(r"(.)\1+", r"\1", t)
    if len(c) < 7 or len(set(c)) < 5 or sum(ch in "aeiouy" for ch in c) / len(c) > 0.2:
        return False
    row = max(sum(ch in r for ch in c) for r in ROWS) / len(c)
    return row >= 0.8 or bool(re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", c))


STOCK_RE = re.compile(r"[A-Z][a-z]+[-_]?[A-Z]?[a-z]+[-_]?\d{1,4}")
ESC_RE = re.compile(r"&(amp|gt|lt);")
SCAM_RE = re.compile(r"https?://[^\s/)\]]+\.(live|life|shop)(?=[/\s)\]]|$)", re.I)
V1 = ("dormant_then_burst", "metronome", "rapid_fire", "farm_subs", "self_repeat", "ai_style", "fast_replies", "topic_hopper")


def _iter(paths):
    for p in ([paths] if isinstance(paths, str) else paths):
        for f in sorted(glob.glob(p)) or [p]:
            if f.endswith(".zip"):
                z = zipfile.ZipFile(f)
                fh = z.open(z.namelist()[0])
            else:
                fh = open(f, "rb")
            with fh:
                for line in fh:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue


def _flags(items, thread_ts, as_of=None, first_ever=None, name=""):
    ts = sorted(float(r["created_utc"]) for r in items)
    comments = [r for r in items if "body" in r and "title" not in r]
    subs = Counter(str(r.get("subreddit") or "").lower() for r in items)
    n = len(items)
    f, m = {}, {"items": n, "comments": len(comments), "subs": len(subs)}
    if n:
        m["first_seen"] = ts[0]
        m["last_seen"] = ts[-1]
    burst, longest = signals.dormancy_then_burst(ts)
    f["dormant_then_burst"] = burst
    m["longest_gap_days"] = longest
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    cv = signals.interval_cv(ts)
    m["interval_cv"] = round(cv, 2) if cv is not None else ""
    f["metronome"] = n >= 30 and cv is not None and cv < 0.5
    fast = sum(g < 60 for g in gaps) / len(gaps) if gaps else 0
    m["share_gaps_under_60s"] = round(fast, 3)
    f["rapid_fire"] = n >= 30 and fast >= 0.2
    farm = sum(c for s, c in subs.items() if s in signals.FARM_SUBS) / n if n else 0
    m["farm_share"] = round(farm, 3)
    f["farm_subs"] = farm >= 0.2
    texts = [(r.get("body") or "").strip().lower() for r in comments if len((r.get("body") or "").split()) >= 4
             and r.get("body") not in ("[deleted]", "[removed]")]
    rep = Counter(texts)
    self_rep = sum(c for c in rep.values() if c > 1) / len(texts) if texts else 0
    m["self_repeat"] = round(self_rep, 3)
    f["self_repeat"] = len(comments) >= 10 and self_rep >= 0.2
    ai = sum(signals.is_ai_style(r.get("body")) for r in comments) / len(comments) if comments else 0
    m["ai_style_share"] = round(ai, 3)
    f["ai_style"] = len(comments) >= 5 and ai >= 0.3
    lat = [float(r["created_utc"]) - thread_ts[r["link_id"]] for r in comments
           if r.get("link_id") in thread_ts and float(r["created_utc"]) >= thread_ts[r["link_id"]]]
    m["median_reply_minutes"] = round(median(lat) / 60, 1) if lat else ""
    m["share_replies_under_10min"] = round(sum(x < 600 for x in lat) / len(lat), 3) if lat else ""
    f["fast_replies"] = len(lat) >= 10 and sum(x < 600 for x in lat) / len(lat) >= 0.5
    top = subs.most_common(1)[0][1] / n if n else 0
    m["top_sub_share"] = round(top, 3)
    m["sub_spread"] = round(signals.entropy_share(subs), 3)
    f["topic_hopper"] = len(subs) >= 20 and top <= 0.10
    # v2 rules
    med_lat = median(lat) / 60 if lat else None
    f["reply_window"] = len(lat) >= 8 and med_lat is not None and 5 <= med_lat <= 15
    spread = signals.entropy_share(subs)
    as_of = as_of or (ts[-1] if ts else 0)
    f["tourist"] = bool(ts) and ts[0] >= as_of - 183 * 86400 and n <= 60 and len(subs) >= 10 and spread >= 0.95
    th = Counter(r.get("link_id") for r in comments)
    back = sum(c > 1 for c in th.values()) / len(th) if th else 0
    toplvl = sum(str(r.get("parent_id") or "").startswith("t3_") for r in comments) / len(comments) if comments else 0
    m["threads_revisited"] = round(back, 3)
    m["top_level_share"] = round(toplvl, 3)
    f["hit_and_run"] = len(th) >= 10 and back <= 0.05 and toplvl >= 0.55
    words = [len((r.get("body") or "").split()) for r in comments if r.get("body") not in ("[deleted]", "[removed]")]
    wmed = median(words) if words else 0
    wmean = sum(words) / len(words) if words else 0
    wcv = (sum((w - wmean) ** 2 for w in words) / len(words)) ** 0.5 / wmean if wmean else 0
    m["words_median"] = wmed
    m["words_cv"] = round(wcv, 3)
    f["uniform_length"] = len(words) >= 10 and wmed >= 25 and wcv <= 0.85
    f["young_account"] = bool(ts) and ts[0] >= as_of - 90 * 86400
    m["first_ever"] = first_ever or ""
    f["young_account_true"] = bool(first_ever) and first_ever >= as_of - 90 * 86400
    # v4 rules
    f["stock_name"] = bool(STOCK_RE.fullmatch(name or ""))
    f["gibberish_name"] = bool(re.fullmatch(r"[a-z]{8,}\d?", name or "")) and _no_word(re.sub(r"\d", "", name))
    texts_all = [(r.get("title") or "") + " " + (r.get("body") or r.get("selftext") or "") for r in items]
    f["escaped_text"] = any(ESC_RE.search(t) for t, r in zip(texts_all, items) if float(r["created_utc"]) >= 1704067200)
    live = [(r.get("body") or "").strip() for r in comments if r.get("body") not in ("[deleted]", "[removed]")]
    quoted = [b for b in live if b and all(l.lstrip().startswith((">", "&gt;")) for l in b.splitlines() if l.strip())]
    m["quoted_share"] = round(len(quoted) / len(live), 3) if live else ""
    f["quoted_comments"] = len(live) >= 5 and len(quoted) / len(live) >= 0.3
    f["mash_comment"] = any(_mash(b) for b in live)
    f["scam_domain"] = any(SCAM_RE.search(t) for t in texts_all + [str(r.get("url") or "") for r in items])
    posts = n - len(comments)
    f["posts_only"] = posts >= 3 and not comments
    # v5 rules
    ai = sum(bool(AI_RE.search(b)) for b in live) / len(live) if live else 0
    m["ai_vocab_share"] = round(ai, 3)
    f["ai_vocab"] = len(live) >= 10 and ai >= 0.1
    mdx = sum(bool(MD_RE.search(b)) or len(BUL_RE.findall(b)) >= 2 for b in live) / len(live) if live else 0
    m["md_share"] = round(mdx, 3)
    f["md_structure"] = len(live) >= 10 and mdx >= 0.1
    cvs = []
    for b in live:
        sl = [len(x.split()) for x in SENT_RE.findall(b) if len(x.split()) >= 2]
        if len(sl) >= 3:
            mu = sum(sl) / len(sl)
            cvs.append((sum((x - mu) ** 2 for x in sl) / len(sl)) ** 0.5 / mu)
    m["sentence_cv"] = round(median(cvs), 3) if cvs else ""
    f["flat_sentences"] = len(cvs) >= 5 and median(cvs) <= 0.3
    from . import sources
    sm = sum(bool(sources.find(t)) for t in texts_all + [str(r.get("url") or "") for r in items if r.get("url")])
    m["state_media_links"] = sm
    f["state_media_link"] = sm >= 2
    # v6 rules (warm-up then politics, resold accounts, inflated volume)
    srt = sorted(items, key=lambda r: float(r["created_utc"]))
    f["political_pivot"] = False
    m["political_early"] = m["political_late"] = ""
    if n >= 20:
        k = int(n * 0.7)
        early = sum(map(_political, srt[:k])) / k
        late = sum(map(_political, srt[k:])) / (n - k)
        m["political_early"], m["political_late"] = round(early, 2), round(late, 2)
        f["political_pivot"] = early <= 0.05 and late >= 0.3
    f["sub_shift"] = False
    if n >= 21:
        tss = [float(r["created_utc"]) for r in srt]
        gap, i = max((tss[j + 1] - tss[j], j) for j in range(n - 1))
        if gap >= 180 * 86400 and i + 1 >= 10 and n - i - 1 >= 10:
            A = {str(r.get("subreddit")).lower() for r in srt[:i + 1]}
            B = {str(r.get("subreddit")).lower() for r in srt[i + 1:]}
            f["sub_shift"] = not (A & B)
    sc = sorted(int(r.get("score") or 0) for r in comments)
    f["low_engagement"] = len(sc) >= 30 and median(sc) <= 1 and sc[int(0.9 * len(sc)) - 1] <= 2
    f["batch_id"] = False   # set in score(), which sees the whole pool
    m["top_subs"] = "; ".join(f"{s} ({c})" for s, c in subs.most_common(5))
    return f, m


def score(history, groups, context=None, out_dir="history_scores", reveal="none", salt=None, as_of=None, oldest=None):
    """history: zips/jsonl from pull_user_histories. groups: groups.csv from screen.shortlist.
    context: posts zip from pull_thread_context (enables the fast_replies rule).
    reveal: "none" hashes every name; "known" shows Bot Bouncer-listed names; "all" shows all (private use).
    as_of: "YYYY-MM-DD" the check date (for the account-age rules).
    oldest: the <name>_oldest.json from pull_user_histories(oldest=True), for true account age."""
    first_ever = json.load(open(oldest)) if oldest else {}
    if isinstance(as_of, str):
        from datetime import datetime, timezone
        as_of = datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc).timestamp()
    group = {r["username"]: (r["group"], r["reasons"]) for r in csv.DictReader(open(groups, encoding="utf-8"))}
    by = defaultdict(list)
    for r in _iter(history):
        a = r.get("author")
        if a in group:
            by[a].append(r)
    thread_ts = {}
    if context:
        for r in _iter(context):
            if r.get("id") and r.get("created_utc"):
                thread_ts["t3_" + r["id"]] = float(r["created_utc"])
    from . import salt as _salt
    salt = _salt.get(salt)
    show = lambda a: a if reveal == "all" or (reveal == "known" and group[a][0] == "known_bot") \
        else "acct_" + hashlib.sha256((salt + a).encode()).hexdigest()[:10]
    fid = {}
    for a, its in by.items():
        for r in its:
            if str(r.get("author_fullname") or "").startswith("t2_"):
                fid[a] = int(r["author_fullname"][3:], 36); break
    ordered = sorted(fid.items(), key=lambda kv: kv[1])
    batch = set()
    for (a1, i1), (a2, i2) in zip(ordered, ordered[1:]):
        if i2 - i1 < 5000:
            batch |= {a1, a2}
    rows, tally = [], defaultdict(Counter)
    sizes = Counter(g for g, _ in group.values())
    for a, (g, why) in group.items():
        items = by.get(a, [])
        f, m = _flags(items, thread_ts, as_of, first_ever.get(a), a)
        f["batch_id"] = a in batch
        nflags = sum(f.values())
        prim = [k for k in PRIMARY if f.get(k)]
        sec = [k for k in SUPPORT if f.get(k)]
        tier = "primary+secondary" if prim and sec else "primary" if prim else ""
        tally[g]["_primary"] += bool(prim)
        tally[g]["_prim_sec"] += bool(prim and sec)
        tally[g]["_with_history"] += bool(items)
        tally[g]["_2plus"] += nflags >= 2
        tally[g]["_v2_2plus"] += sum(v for k, v in f.items() if k not in V1 and k not in V3 and k not in V4 and k not in V5 and k not in V6) >= 2
        tally[g]["_v5_any"] += any(f[k] for k in V5)
        tally[g]["_v6_any"] += any(f[k] for k in V6)
        tally[g]["_prim_sec_nostock"] += bool(prim) and any(f.get(k) for k in SUPPORT if k != "stock_name")
        import math
        z = WEIGHTS["_intercept"] + sum(w for k, w in WEIGHTS.items() if k != "_intercept" and f.get(k))
        bscore = 1 / (1 + math.exp(-z))
        tally[g]["_score_high"] += bscore >= 0.5
        tally[g]["_v4_any"] += any(f[k] for k in V4 if k != "stock_name")
        for k, v in f.items():
            tally[g][k] += v
        rows.append({"account": show(a), "group": g, "screen_reasons": why, "flags": nflags, "tier": tier, "bot_score": round(bscore, 3),
                     "flag_list": "+".join(k for k, v in f.items() if v), **m})
    os.makedirs(out_dir, exist_ok=True)
    rows.sort(key=lambda r: (-r["flags"], r["group"]))
    fields = list(dict.fromkeys(k for r in rows for k in r)) if rows else []
    with open(os.path.join(out_dir, "accounts.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out_dir, "flagged_shortlist.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
        w.writerows(r for r in rows if r["group"] == "shortlist" and r["flags"] >= 2)
    main = ("later_bot", "known_bot", "round1_bot", "shortlist", "control")
    order = [g for g in main if sizes[g]] + sorted(g for g in sizes if g not in main)
    pct = lambda g, k: f"{100 * tally[g][k] / max(1, tally[g]['_with_history']):.0f}%"
    md = ["# History scores", "", "Share of accounts in each group where the flag fired (accounts with any history).", "",
          "| Flag | Rule | " + " | ".join(f"{g} (n={tally[g]['_with_history']})" for g in order) + " |",
          "|---|---|" + "---|" * len(order)]
    for k, rule in RULES.items():
        md.append(f"| {k} | {rule} | " + " | ".join(pct(g, k) for g in order) + " |")
    md.append("| 2+ flags | | " + " | ".join(pct(g, "_2plus") for g in order) + " |")
    md.append("| 2+ v2 flags | reply_window, tourist, hit_and_run, uniform_length | " + " | ".join(pct(g, "_v2_2plus") for g in order) + " |")
    md.append("| any v4 flag | any v4 rule except stock_name | " + " | ".join(pct(g, "_v4_any") for g in order) + " |")
    md.append("| any primary | " + ", ".join(PRIMARY) + " | " + " | ".join(pct(g, "_primary") for g in order) + " |")
    md.append("| bot_score 0.5+ | weighted score (history.WEIGHTS) of at least 0.5 | " + " | ".join(pct(g, "_score_high") for g in order) + " |")
    md.append("| primary + secondary | a primary flag plus any SUPPORT flag | " + " | ".join(pct(g, "_prim_sec") for g in order) + " |")
    md.append("| primary + secondary (excluding stock_name) | | " + " | ".join(pct(g, "_prim_sec_nostock") for g in order) + " |")
    md.append("| any v6 flag | political_pivot, sub_shift, low_engagement, batch_id | " + " | ".join(pct(g, "_v6_any") for g in order) + " |")
    md.append("| any v5 flag | ai_vocab, md_structure, flat_sentences, state_media_link | " + " | ".join(pct(g, "_v5_any") for g in order) + " |")
    # How often a flag would be right at realistic bot rates (precision), pooling the labelled bot groups
    bots = [g for g in order if g.endswith("bot") and g != "earlier_round_bot"]
    nb = sum(tally[g]["_with_history"] for g in bots); nc = tally["control"]["_with_history"]
    if nb and nc:
        def ppv(k, prev):
            tpr = sum(tally[g][k] for g in bots) / nb; fpr = tally["control"][k] / nc
            return "" if tpr == 0 else f"{100 * prev * tpr / (prev * tpr + (1 - prev) * fpr):.0f}%" if fpr else "100%*"
        md += ["", f"## If a flag fires, how likely is the account a bot? (bots pooled: {', '.join(bots)}, n={nb}; controls n={nc})", "",
               "Precision at an assumed share of bots among active accounts. The catch and false-alarm rates come from the table above; "
               "* means no control tripped it, so precision is unmeasured, not perfect. Bot share in these subs is unknown: 1% and 5% bracket it.", "",
               "| Flag | Bots caught | Controls flagged | Precision if 1% are bots | if 5% are bots |", "|---|---|---|---|---|"]
        keys = list(RULES) + ["_primary", "_prim_sec", "_prim_sec_nostock", "_score_high"]
        for k in keys:
            tp = sum(tally[g][k] for g in bots)
            if tp:
                md.append(f"| {k.strip('_')} | {100 * tp / nb:.0f}% | {100 * tally['control'][k] / nc:.0f}% | {ppv(k, 0.01)} | {ppv(k, 0.05)} |")
    md += ["", "A useful flag fires far more for known bots than for controls. The control column is the false-alarm rate:",
           "a flag firing for 10% of controls would wrongly flag about 1 in 10 ordinary accounts.",
           f"Accounts with no history found (deleted, suspended or never active): "
           + ", ".join(f"{g} {sizes[g] - tally[g]['_with_history']}" for g in order) + "."]
    open(os.path.join(out_dir, "comparison.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    return os.path.join(out_dir, "comparison.md")


def context_summary(context, history, groups, out_dir="history_scores", top=15):
    """What the threads each group comments in are about: their subs and most common title words."""
    group = {r["username"]: r["group"] for r in csv.DictReader(open(groups, encoding="utf-8"))}
    posts = {"t3_" + r["id"]: r for r in _iter(context) if r.get("id")}
    subs, words = defaultdict(Counter), defaultdict(Counter)
    stop = set("the a an and or to of in on for is are was be with this that it at by from as my your his her their "
               "i you he she they we what why how who when not no yes just".split())
    for r in _iter(history):
        g = group.get(r.get("author"))
        p = posts.get(r.get("link_id"))
        if not g or not p:
            continue
        subs[g][p.get("subreddit", "")] += 1
        words[g].update({w for w in re.findall(r"[a-z']{3,}", (p.get("title") or "").lower()) if w not in stop})
    md = ["# Where each group comments", ""]
    for g in ("known_bot", "shortlist", "control"):
        if subs[g]:
            md += [f"## {g}", "", "Subreddits of threads: " + ", ".join(f"r/{s} ({c})" for s, c in subs[g].most_common(top)),
                   "", "Title words: " + ", ".join(f"{w} ({c})" for w, c in words[g].most_common(top)), ""]
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "context_summary.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
