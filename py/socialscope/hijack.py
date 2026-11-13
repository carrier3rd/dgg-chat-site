"""Candidate rules for hijacked or resold accounts used for solicitation spam (frozen Nov 1, 2026, before testing).

Found by hand in the Nov 1 label audit (docs/label-audit.md): most aged accounts Bot Bouncer bans in these subs have an
ordinary multi-year history followed by sexual-solicitation posts in NSFW subreddits carrying a Telegram, Snapchat or
Instagram handle. Exploratory numbers on that same sample (not a test): handle template 31 of 60 banned aged accounts
vs 1 of 60 random; broad 50 of 60 vs 7 of 60. Both rules await a fresh frozen test.

items: list of dicts with created_utc, subreddit, and body (comments) or title/selftext (posts)."""
import re

DAY = 86400
HANDLE = re.compile(r"\b(?:t[e3]l[e3]?g?r?a?m|tg|tele|snap(?:chat)?|sn[a-z]*ch?at|lnst[a-z]*|insta)\b\s*[:@]"
                    r"|\b(?:[fF]\s?(?:1[89]|2\d)|\d\d\s?\[?[fF]4[mM]\]?)\b|ask (?:for )?(?:my )?menu|sexting|\bgfe\b|hit me"
                    r"|[\U0001D5A0-\U0001D5FF]{3}", re.I)
NSFW_SUB = re.compile(r"(?:nsfw|gonewild|nude|sex|horny|onlyfans|hookup|h00kup|cuckold|swinger|jerk|slut|milf|teen|r4r"
                      r"|fetish|cam$|bdsm|sexting)", re.I)


def _is_post(x):
    return "title" in x


def _text(x):
    return x.get("body") if "body" in x else f"{x.get('title') or ''} {x.get('selftext') or ''}"


def solicit_handle(items, min_posts=2):
    """Strict: 2+ submissions whose text carries a contact-handle or solicitation template."""
    return sum(1 for x in items if _is_post(x) and HANDLE.search(_text(x) or "")) >= min_posts


def solicit_broad(items, min_nsfw_posts=3, min_prior=50, prior_gap_days=90):
    """Broad: strict rule, or 3+ submissions to NSFW subs on an account with 50+ non-NSFW items posted at least
    90 days before its first NSFW submission (an established history that then turns)."""
    if solicit_handle(items):
        return True
    nsfw = sorted(int(x["created_utc"]) for x in items if _is_post(x) and NSFW_SUB.search(str(x.get("subreddit") or "")))
    if len(nsfw) < min_nsfw_posts:
        return False
    cut = nsfw[0] - prior_gap_days * DAY
    prior = sum(1 for x in items if int(x["created_utc"]) < cut and not NSFW_SUB.search(str(x.get("subreddit") or "")))
    return prior >= min_prior
