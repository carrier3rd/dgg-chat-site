"""Live account facts from Reddit's official API (written Nov 13, 2026).

This adds to Arctic Shift without replacing it. The v7.1 score stays on Arctic Shift data, which it was trained on.
Reddit's API omits deleted and removed items, so its features would differ. This module only adds facts Arctic
Shift lacks: whether the account is active, suspended or not found, its exact creation date, karma, verified email,
and how much it has posted since Arctic Shift's copy. None of these feed the score.

Credentials: the user registers a Reddit "script" app at https://www.reddit.com/prefs/apps and writes
~/socialscope_data/secrets/reddit_api.json (mode 600, never committed, never printed):
    {"client_id": "...", "client_secret": "..."}
App-only OAuth (client_credentials), so no Reddit password is ever stored. Reddit allows about 100 requests a
minute per client; a lookup uses 3.

Usage:
    from socialscope import reddit_api
    facts = reddit_api.account_facts("name", arctic_last=..., arctic_oldest=...)   # None if not configured
"""
import base64, json, os, time, urllib.error, urllib.parse, urllib.request

CRED = os.path.expanduser("~/socialscope_data/secrets/reddit_api.json")
UA = "linux:socialscope-lookup:0.1 (research tool; read-only)"
_TOKEN = {}


class NotConfigured(Exception):
    pass


def _token():
    if _TOKEN.get("exp", 0) > time.time() + 60:
        return _TOKEN["tok"]
    if not os.path.exists(CRED):
        raise NotConfigured(f"no credentials file at {CRED}")
    c = json.load(open(CRED))
    if not c.get("client_id") or not c.get("client_secret"):
        raise NotConfigured("credentials file is missing client_id or client_secret")
    auth = base64.b64encode(f"{c['client_id']}:{c['client_secret']}".encode()).decode()
    req = urllib.request.Request("https://www.reddit.com/api/v1/access_token",
                                 data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
                                 headers={"Authorization": "Basic " + auth, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    if "access_token" not in j:
        raise NotConfigured("Reddit refused the credentials: " + str(j.get("error", "unknown error")))
    _TOKEN.update(tok=j["access_token"], exp=time.time() + float(j.get("expires_in", 3600)))
    return _TOKEN["tok"]


def _get(path, params=None, tries=3):
    url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode(dict(params or {}, raw_json=1))
    for a in range(tries):
        req = urllib.request.Request(url, headers={"Authorization": "bearer " + _token(), "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                left = r.headers.get("x-ratelimit-remaining")
                if left is not None and float(left) < 2:
                    time.sleep(float(r.headers.get("x-ratelimit-reset") or 10))
                return 200, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                return e.code, None
            if e.code == 401:
                _TOKEN.clear()
            elif e.code not in (429, 500, 502, 503, 504) or a == tries - 1:
                raise
            time.sleep(5 * (a + 1))
    return None, None


def facts_from(about_code, about, overview, arctic_last=None, arctic_oldest=None):
    """Turn raw API answers into the card's facts. Separate from the network so it can be tested on fixtures."""
    out = {"source": "Reddit API", "checked_utc": time.time()}
    if about_code == 404:
        out["status"] = "not found"
        out["status_note"] = "Reddit says no such account: deleted, shadowbanned, or the name changed."
        return out
    if about_code == 403:
        out["status"] = "unavailable"
        out["status_note"] = "Reddit refused the request."
        return out
    d = (about or {}).get("data") or {}
    if d.get("is_suspended"):
        out["status"] = "suspended"
        out["status_note"] = "Reddit has suspended this account."
        return out
    out["status"] = "active"
    out["created_utc"] = d.get("created_utc")
    for k in ("link_karma", "comment_karma", "total_karma", "has_verified_email", "verified", "is_mod", "is_employee"):
        if k in d:
            out[k] = d[k]
    if out.get("created_utc") and arctic_oldest:
        out["days_to_first_item"] = (float(arctic_oldest) - float(out["created_utc"])) / 86400
    kids = [c.get("data", {}) for c in ((overview or {}).get("data") or {}).get("children", [])]
    ts = [float(k["created_utc"]) for k in kids if k.get("created_utc")]
    out["recent_seen"] = len(ts)
    if ts:
        out["newest_utc"] = max(ts)
        if arctic_last:
            out["newer_than_arctic"] = sum(t > float(arctic_last) for t in ts)
    return out


def account_facts(user, arctic_last=None, arctic_oldest=None):
    """Live facts for one account, or None if credentials aren't set up. Never raises for a missing account."""
    try:
        code, about = _get(f"/user/{urllib.parse.quote(user)}/about")
        ov = None
        if code == 200 and not ((about or {}).get("data") or {}).get("is_suspended"):
            _, ov = _get(f"/user/{urllib.parse.quote(user)}/overview", {"limit": 100, "sort": "new"})
        return facts_from(code, about, ov, arctic_last, arctic_oldest)
    except NotConfigured:
        return None
