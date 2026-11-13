"""Small reusable signal functions shared by the screen and history scorers."""
import math, re
from statistics import mean, pstdev

STOCK_PHRASES = re.compile(
    r"doing a lot of heavy lifting|is sending me|pure cinema|it tracks|kinda here for it|lives rent free|"
    r"the way (?:you|he|she|they) (?:described|said|wrote)|this is giving|not the \w+ \w+ing|"
    r"i'm (?:so )?here for (?:it|this)|chef'?s kiss|main character energy|unhinged in the best way", re.I)
SIMILE = re.compile(r"\blike (?:it|he|she|they|someone|watching|a|an) [a-z]+(?: [a-z]+){1,}", re.I)
DEFAULT_NAME = re.compile(r"^[A-Z][a-z]+[-_]?[A-Z][a-z]+[-_]?\d{2,4}$")
FARM_SUBS = {s.lower() for s in (
    "FreeKarma4U", "FreeKarma4You", "FreeKarmaForYou", "KarmaFarming4Pros", "karma", "FreeKarma",
    "GetMoreKarma", "upvote", "Karma4Free", "karmafarm", "FreeKarmaSub", "KarmaStore")}


def ai_style_score(text):
    """0-5 points for the lowercase-quip template found in the Oct 2026 r/Destiny wave.
    Points: starts lowercase; vivid simile; stock reaction phrase; a second short aside paragraph;
    15-70 words with no question. Score 3+ with a simile or stock phrase counts as AI-style."""
    t = (text or "").strip()
    if not t or t.startswith(("http", "![", ">")):
        return 0
    words = len(t.split())
    pts = 0
    pts += t[0].islower()
    sim = bool(SIMILE.search(t))
    stock = bool(STOCK_PHRASES.search(t))
    pts += sim + stock
    pts += bool(re.search(r"\n\s*\n|\S {3,}\S", t)) and words < 90
    pts += 15 <= words <= 70 and "?" not in t
    return pts if (sim or stock) else min(pts, 2)


def is_ai_style(text, threshold=3):
    return ai_style_score(text) >= threshold


def account_id_number(fullname):
    """Reddit account IDs (t2_xxx) are base-36 counters in sign-up order: higher = newer."""
    try:
        return int(str(fullname)[3:], 36) if str(fullname).startswith("t2_") else None
    except ValueError:
        return None


def interval_cv(timestamps):
    ts = sorted(timestamps)
    gaps = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    return pstdev(gaps) / mean(gaps) if len(gaps) >= 2 else None


def hour_entropy(timestamps):
    n = len(timestamps)
    if not n:
        return None
    counts = {}
    for t in timestamps:
        h = int((t % 86400) // 3600)
        counts[h] = counts.get(h, 0) + 1
    return -sum((c / n) * math.log(c / n) for c in counts.values()) / math.log(24)


def dormancy_then_burst(timestamps, min_gap_days=180, burst_items=20, burst_days=30):
    """True when a silence of min_gap_days+ is followed by burst_items+ items within burst_days.
    The signature of an aged account that was bought or taken over. Returns (flag, longest_gap_days)."""
    ts = sorted(timestamps)
    longest, flag = 0.0, False
    for i in range(1, len(ts)):
        gap = (ts[i] - ts[i - 1]) / 86400
        longest = max(longest, gap)
        if gap >= min_gap_days:
            after = [t for t in ts[i:] if t - ts[i] <= burst_days * 86400]
            if len(after) >= burst_items:
                flag = True
    return flag, round(longest, 1)


def entropy_share(counts):
    """Normalized entropy of a {key: count} dict: 0 = all in one place, 1 = evenly spread."""
    n = sum(counts.values())
    if n == 0 or len(counts) < 2:
        return 0.0
    return -sum((c / n) * math.log(c / n) for c in counts.values() if c) / math.log(len(counts))
