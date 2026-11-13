"""
Ban-relative pre-window features (socialscope/prewindow.py).

Given a single account's history (list of dict items with `created_utc`, `subreddit`,
`body` or `title`, `score`, and optional `url`) and an `anchor_utc` timestamp (e.g., the
Bot Bouncer listing date, or a check date for unlabeled accounts), computes behavioral
features in the 30 days immediately preceding the anchor (`[anchor_utc - 30d, anchor_utc]`)
compared with the account's own earlier baseline history (`< anchor_utc - 30d`).

All functions are pure and deterministic.
"""

from __future__ import annotations

import re
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


DAY_SECONDS = 86400.0
DEFAULT_WINDOW_DAYS = 30
SHORT_COMMENT_MAX_CHARS = 20
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def extract_text(item: Dict[str, Any]) -> str:
    """Return text content of a history item (prefers `body` for comments, else `title` + `selftext`)."""
    body = item.get("body")
    if isinstance(body, str) and body.strip():
        return body.strip()
    title = item.get("title") or ""
    selftext = item.get("selftext") or ""
    combined = f"{title} {selftext}".strip()
    return combined


def is_comment_item(item: Dict[str, Any]) -> bool:
    """Determine whether an item is a comment (vs. a link/self submission)."""
    if "body" in item and item.get("body") is not None and "title" not in item:
        return True
    kind = str(item.get("kind") or item.get("type") or "").lower()
    if kind in {"comment", "t1"}:
        return True
    if kind in {"post", "submission", "t3"}:
        return False
    return "body" in item and item.get("body") is not None


def has_external_link(item: Dict[str, Any]) -> bool:
    """Return True if the item contains an HTTP(S) URL in its text or is an external link post."""
    text = extract_text(item)
    if URL_RE.search(text):
        return True
    url = item.get("url")
    # Arctic Shift gives self posts a reddit.com url and slim pulls drop is_self, so reddit links count as internal
    if isinstance(url, str) and url.strip() and not re.search(r"^https?://(?:[a-z]+\.)?reddit\.com/|^/r/", url):
        # Exclude internal reddit self-post permalinks if marked is_self
        if item.get("is_self") is True:
            return False
        if URL_RE.search(url):
            return True
    return False


def partition_history(
    items: Iterable[Dict[str, Any]],
    anchor_utc: float | int,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filter items up to `anchor_utc` and partition into `(earlier_items, window_items)`.

    - `earlier_items`: `created_utc < anchor_utc - window_days * 86400`
    - `window_items`: `anchor_utc - window_days * 86400 <= created_utc <= anchor_utc`
    - Items with `created_utc > anchor_utc` or missing/invalid `created_utc` are ignored.
    Both returned lists are sorted ascending by `created_utc`.
    """
    anchor = float(anchor_utc)
    window_start = anchor - (window_days * DAY_SECONDS)

    earlier: List[Dict[str, Any]] = []
    window: List[Dict[str, Any]] = []

    for raw in items:
        if not isinstance(raw, dict):
            continue
        ts_val = raw.get("created_utc")
        if ts_val is None:
            continue
        try:
            ts = float(ts_val)
        except (ValueError, TypeError):
            continue

        if ts > anchor:
            continue
        if ts < window_start:
            earlier.append(raw)
        else:
            window.append(raw)

    earlier.sort(key=lambda x: float(x["created_utc"]))
    window.sort(key=lambda x: float(x["created_utc"]))
    return earlier, window


def compute_new_subreddit_share(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
) -> float:
    """
    Share of window items posted in subreddits where the account never posted before the window.
    Returns 0.0 if `window_items` is empty. If `earlier_items` is empty and `window_items` is non-empty,
    all window subreddits are new relative to prior history (returns 1.0).
    """
    if not window_items:
        return 0.0
    earlier_subs: Set[str] = {
        str(it.get("subreddit") or "").strip().lower()
        for it in earlier_items
        if str(it.get("subreddit") or "").strip()
    }
    valid_window = [
        str(it.get("subreddit") or "").strip().lower()
        for it in window_items
        if str(it.get("subreddit") or "").strip()
    ]
    if not valid_window:
        return 0.0
    new_count = sum(1 for s in valid_window if s not in earlier_subs)
    return new_count / len(valid_window)


def compute_distinct_subs_per_item(window_items: Sequence[Dict[str, Any]]) -> float:
    """
    Ratio of distinct subreddits in the window to total items in the window (`[0.0, 1.0]`).
    Returns 0.0 if `window_items` is empty.
    """
    if not window_items:
        return 0.0
    subs = {
        str(it.get("subreddit") or "").strip().lower()
        for it in window_items
        if str(it.get("subreddit") or "").strip()
    }
    return len(subs) / len(window_items)


def compute_posting_rate_ratio(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
    anchor_utc: float | int,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> float:
    """
    Ratio of daily posting rate in the window (`len(window) / window_days`) to the baseline
    daily posting rate before the window (`len(earlier) / earlier_span_days`).

    `earlier_span_days` is measured from the first earlier item's timestamp to `window_start`,
    floored at 1.0 day to prevent division by zero.
    Returns 0.0 if either `window_items` or `earlier_items` is empty.
    """
    if not window_items or not earlier_items:
        return 0.0
    window_start = float(anchor_utc) - (window_days * DAY_SECONDS)
    first_earlier_ts = float(earlier_items[0]["created_utc"])
    earlier_span_days = max(1.0, (window_start - first_earlier_ts) / DAY_SECONDS)

    window_rate = len(window_items) / float(max(1, window_days))
    earlier_rate = len(earlier_items) / earlier_span_days
    if earlier_rate <= 0.0:
        return 0.0
    return window_rate / earlier_rate


def compute_median_length_ratio(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
) -> float:
    """
    Ratio of median character length of items in the window to median character length of earlier items.
    Returns 0.0 if either period has no items or if earlier median length is 0.
    """
    if not window_items or not earlier_items:
        return 0.0
    earlier_lengths = [len(extract_text(it)) for it in earlier_items]
    window_lengths = [len(extract_text(it)) for it in window_items]

    med_earlier = float(median(earlier_lengths))
    med_window = float(median(window_lengths))
    if med_earlier <= 0.0:
        return 0.0
    return med_window / med_earlier


def compute_link_share_change(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
) -> float:
    """
    Change in share of items containing links (`window_link_share - earlier_link_share`).
    Returns 0.0 if either `window_items` or `earlier_items` is empty.
    """
    if not window_items or not earlier_items:
        return 0.0
    earlier_share = sum(1 for it in earlier_items if has_external_link(it)) / len(earlier_items)
    window_share = sum(1 for it in window_items if has_external_link(it)) / len(window_items)
    return window_share - earlier_share


def compute_short_comment_share(
    window_items: Sequence[Dict[str, Any]],
    max_chars: int = SHORT_COMMENT_MAX_CHARS,
) -> float:
    """
    Share of comments in the window (or all window items if none are explicitly typed) whose
    text is shorter than or equal to `max_chars` characters (default 20 chars).
    Returns 0.0 if the window has no comments/items.
    """
    if not window_items:
        return 0.0
    comments = [it for it in window_items if is_comment_item(it)]
    target_pool = comments if comments else list(window_items)
    if not target_pool:
        return 0.0
    short_count = sum(1 for it in target_pool if len(extract_text(it)) <= max_chars)
    return short_count / len(target_pool)


def compute_score_median_change(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
) -> float:
    """
    Difference in median item score between the window and earlier history (`median(window) - median(earlier)`).
    Returns 0.0 if either period has no valid numeric scores.
    """
    if not window_items or not earlier_items:
        return 0.0

    def _scores(pool: Sequence[Dict[str, Any]]) -> List[float]:
        out: List[float] = []
        for it in pool:
            val = it.get("score")
            if val is not None:
                try:
                    out.append(float(val))
                except (ValueError, TypeError):
                    continue
        return out

    s_earlier = _scores(earlier_items)
    s_window = _scores(window_items)
    if not s_earlier or not s_window:
        return 0.0
    return float(median(s_window) - median(s_earlier))


def compute_longest_silence_before_window(
    earlier_items: Sequence[Dict[str, Any]],
    window_items: Sequence[Dict[str, Any]],
    anchor_utc: float | int,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> float:
    """
    Longest inactivity gap (in days) occurring before or leading into the 30-day window.
    Specifically considers:
    - Consecutive timestamps within `earlier_items`
    - The transition gap from the last `earlier_item` to the first `window_item` (or to `window_start`
      if `window_items` is empty).
    Returns 0.0 if `earlier_items` is empty.
    """
    if not earlier_items:
        return 0.0

    timestamps = [float(it["created_utc"]) for it in earlier_items]
    max_gap_sec = 0.0
    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i - 1]
        if gap > max_gap_sec:
            max_gap_sec = gap

    if window_items:
        first_window_ts = float(window_items[0]["created_utc"])
        transition_gap = first_window_ts - timestamps[-1]
    else:
        window_start = float(anchor_utc) - (window_days * DAY_SECONDS)
        transition_gap = max(0.0, window_start - timestamps[-1])

    if transition_gap > max_gap_sec:
        max_gap_sec = transition_gap

    return max_gap_sec / DAY_SECONDS


def compute_prewindow_features(
    items: Iterable[Dict[str, Any]],
    anchor_utc: float | int,
    window_days: int = DEFAULT_WINDOW_DAYS,
    short_comment_max_chars: int = SHORT_COMMENT_MAX_CHARS,
) -> Dict[str, float | int]:
    """
    Compute all ban-relative 30-day pre-window features for an account's history relative to `anchor_utc`.

    Returns a dictionary containing:
        - `window_items`: count of items in `[anchor_utc - 30d, anchor_utc]`
        - `earlier_items`: count of items strictly before `anchor_utc - 30d`
        - `new_subreddit_share`: share of window items in subreddits unseen in earlier history
        - `distinct_subs_per_item`: distinct subreddits in window / total window items
        - `posting_rate_ratio`: daily rate in window / daily rate in earlier history
        - `median_length_ratio`: median text length in window / median text length in earlier history
        - `link_share_change`: link item share in window minus link item share in earlier history
        - `short_comment_share`: share of window comments with length <= `short_comment_max_chars`
        - `score_median_change`: median score in window minus median score in earlier history
        - `longest_silence_before_window`: longest gap in days across earlier items and transition into window
    """
    earlier, window = partition_history(items, anchor_utc=anchor_utc, window_days=window_days)

    return {
        "window_items": len(window),
        "earlier_items": len(earlier),
        "new_subreddit_share": round(compute_new_subreddit_share(earlier, window), 6),
        "distinct_subs_per_item": round(compute_distinct_subs_per_item(window), 6),
        "posting_rate_ratio": round(
            compute_posting_rate_ratio(earlier, window, anchor_utc=anchor_utc, window_days=window_days), 6
        ),
        "median_length_ratio": round(compute_median_length_ratio(earlier, window), 6),
        "link_share_change": round(compute_link_share_change(earlier, window), 6),
        "short_comment_share": round(
            compute_short_comment_share(window, max_chars=short_comment_max_chars), 6
        ),
        "score_median_change": round(compute_score_median_change(earlier, window), 6),
        "longest_silence_before_window": round(
            compute_longest_silence_before_window(
                earlier, window, anchor_utc=anchor_utc, window_days=window_days
            ),
            6,
        ),
    }
