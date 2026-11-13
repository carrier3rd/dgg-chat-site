"""One-account lookup core: v7.1 score, 1-10 rating and descriptive signals (written Nov 13, 2026).

Pure standard library, so the same file runs on the laptop (scripts/lookup.py) and in the visitor's browser
(the site's Lookup tab, through Pyodide). Nothing here touches the network or the disk outside a temp folder.

The score is the frozen v7.1 full model (repull/out/model_repull.pkl), exported as plain trees by
scripts/export_lookup_model.py. Features are built the way scripts/repull_run/feats.py builds them, anchor at the
account's last item. scripts/lookup_parity.py checks both against the original pipeline.

The 1-10 rating is a display scale only (added Nov 13 at the user's request). It is piecewise linear in log10(score)
through fixed points: 0.0001 -> 1, the 5% line -> 5, the 2% line -> 7, the strict (1%) line -> 9, 1.0 -> 10. So
5 and up means flagged at the loose line, 7 and up at the 2% line, 9 and up at the strict line. The score and
lines are unchanged.

Time-zone method, US list and mismatch rule: frozen in docs/lookup-predictions.md.
"""
import collections, csv, json, math, os, re, tempfile

from . import hijack, history, prewindow, signals

# --- copied from scripts/repull_run (common.py KEEP/REMOVED/slim, feats.py removed-text handling) ---------------
KEEP = ("id", "created_utc", "subreddit", "body", "title", "selftext", "score", "link_id", "parent_id", "url",
        "author_fullname", "distinguished")
REMOVED = ("[removed]", "[deleted]")


def slim(r):
    d = {k: r[k] for k in KEEP if k in r}
    for k in ("body", "selftext"):
        if d.get(k):
            d[k] = d[k][:1500]
    d["author"] = r.get("author")
    return d


def _is_removed_comment(x):
    return "body" in x and "title" not in x and (x.get("body") or "").strip() in REMOVED


def _text_clean(x):
    if _is_removed_comment(x):
        return None
    if "title" in x and (x.get("selftext") or "").strip() in REMOVED:
        y = dict(x)
        y["selftext"] = ""
        return y
    return x


def prewindow_features(items, anchor):
    f = prewindow.compute_prewindow_features(items, anchor)
    earlier, window = prewindow.partition_history(items, anchor)
    rem = sum(1 for x in window if _is_removed_comment(x) or ("title" in x and (x.get("selftext") or "").strip() in REMOVED))
    f["removed_share"] = round(rem / len(window), 6) if window else 0.0
    te = [y for y in (_text_clean(x) for x in earlier) if y is not None]
    tw = [y for y in (_text_clean(x) for x in window) if y is not None]
    f["median_length_ratio"] = round(prewindow.compute_median_length_ratio(te, tw), 6)
    f["link_share_change"] = round(prewindow.compute_link_share_change(te, tw), 6)
    f["short_comment_share"] = round(prewindow.compute_short_comment_share(tw), 6)
    return f


# --- frozen in docs/lookup-predictions.md (Nov 13, 2026) -------------------------------------------------------
MIN_ITEMS = 100
QUIET_HOURS = 6
NO_RHYTHM = 0.12
LOCAL_CENTER = 4
US_SHARE = 0.10
US_BAND = (-10, -3)
US_POLITICS = set("""politics conservative republican republicans democrats democrat liberal progressive centrist
moderatepolitics politicaldiscussion askpolitics ezraklein joerogan neoliberal thebulwark samharris askconservatives
askaliberal asktrumpsupporters trump donaldtrump the_donald conservatives libertarian walkaway enoughtrumpspam""".split())
US_PLACES = set("""nyc newyorkcity brooklyn queens bronx manhattan statenisland longisland nj newjersey philadelphia
pittsburgh pennsylvania boston massachusetts providence rhodeisland connecticut vermont newhampshire maine baltimore
maryland washingtondc dc nova virginia richmond northcarolina charlotte raleigh asheville southcarolina charleston
atlanta georgia florida miami orlando tampa jacksonville alabama birmingham mississippi tennessee nashville memphis
kentucky louisville ohio columbus cleveland cincinnati michigan detroit grandrapids indiana indianapolis illinois chicago
wisconsin milwaukee madison minnesota minneapolis twincities iowa desmoines missouri stlouis kansascity kansas nebraska
omaha oklahoma okc tulsa arkansas louisiana neworleans texas houston dallas austin sanantonio elpaso fortworth
newmexico albuquerque arizona phoenix tucson colorado denver boulder utah saltlakecity nevada lasvegas reno idaho boise
montana wyoming northdakota southdakota california losangeles la sanfrancisco bayarea sandiego sacramento oakland
sanjose orangecounty oregon portland washington seattle spokane alaska anchorage hawaii honolulu westvirginia
delaware""".split())
US_SUBS = US_PLACES | US_POLITICS
OTHER_PLACES = {
    "canada": "Canada", "toronto": "Toronto", "vancouver": "Vancouver", "montreal": "Montreal", "ontario": "Ontario",
    "unitedkingdom": "UK", "uk": "UK", "london": "London", "casualuk": "UK", "ireland": "Ireland", "scotland": "Scotland",
    "australia": "Australia", "sydney": "Sydney", "melbourne": "Melbourne", "newzealand": "New Zealand",
    "india": "India", "indiaspeaks": "India", "pakistan": "Pakistan", "bangladesh": "Bangladesh", "nigeria": "Nigeria",
    "kenya": "Kenya", "southafrica": "South Africa", "philippines": "Philippines", "indonesia": "Indonesia",
    "malaysia": "Malaysia", "singapore": "Singapore", "vietnam": "Vietnam", "thailand": "Thailand",
    "germany": "Germany", "de": "Germany", "france": "France", "europe": "Europe", "netherlands": "Netherlands",
    "poland": "Poland", "ukraine": "Ukraine", "russia": "Russia", "serbia": "Serbia", "romania": "Romania",
    "israel": "Israel", "turkey": "Turkey", "iran": "Iran", "egypt": "Egypt", "brazil": "Brazil", "mexico": "Mexico",
    "argentina": "Argentina", "japan": "Japan", "korea": "Korea", "china": "China", "taiwan": "Taiwan",
}
# ----------------------------------------------------------------------------------------------------------------

STOP = set("""a about above after again against all am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few for from
further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how
how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my myself no nor not of off on
once only or other ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such
than that that's the their theirs them themselves then there there's these they they'd they'll they're they've this those
through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's
which while who who's whom why why's with won't would wouldn't you you'd you'll you're you've your yours yourself
yourselves just like get got one really think people also even going know much make way want see well thing things still
yeah lol good right sure actually say said something never every lot many will now would could
http https www com removed deleted gt amp nbsp""".split())
EN_COMMON = {"the", "and", "is", "to", "of", "a", "in", "that", "it", "you", "for", "this", "i", "not", "are", "be", "with"}
WORD = re.compile(r"[a-z][a-z'\-]{2,}")


# --- model -----------------------------------------------------------------------------------------------------
def _fl(x):
    if x is None or x == "":
        return math.nan
    return float(x)


def feature_vector(row, M):
    """Same columns and order as scripts/repull_run/score.py matrix(), restricted to the model's columns."""
    vals = [_fl(row.get(c)) for c in M["num"]] + [_fl(row["hist_age"]), _fl(row["true_age"]), float(row["sh"]), float(row["sb"]),
            float(row["primary"]), math.log1p(row["n_cut"])] + [_fl(row.get("pw_" + k)) for k in M["pwk"] if k != "removed_share"]
    return [vals[j] for j in M["ok"]]


def predict(M, x):
    """HistGradientBoostingClassifier.predict_proba[:, 1] from the exported trees (same walk, same summation order)."""
    raw = M["baseline"]
    for tree in M["trees"]:
        i = 0
        while True:
            f, thr, mleft, left, right, value, leaf = tree[i]
            if leaf:
                raw += value
                break
            v = x[f]
            i = (left if mleft else right) if v != v else (left if v <= thr else right)
    return 1.0 / (1.0 + math.exp(-raw))


def rating(p, th):
    """1-10 display scale (see module docstring). Unrounded; displays cut it to two decimals (user, Nov 13: no rounding)."""
    pts = [(math.log10(1e-4), 1.0), (math.log10(th["5%"]), 5.0), (math.log10(th["2%"]), 7.0), (math.log10(th["1%"]), 9.0), (0.0, 10.0)]
    x = math.log10(min(max(p, 1e-4), 1.0))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 10.0


def rating_text(r):
    """Two decimals, truncated not rounded: 1.928 -> '1.92'. The 1e-9 keeps 5.0 from showing as 4.99."""
    return f"{math.floor(r * 100 + 1e-9) / 100:.2f}"


def verdict(p, th):
    if p >= th["1%"]:
        return "hi", "Flagged at the strict line (1% target). A lead for review, not proof."
    if p >= th["2%"]:
        return "mid", "Flagged at the 2% line. A weak lead."
    if p >= th["5%"]:
        return "mid", "Above the loose 5% line only. About 7 in 100 ordinary accounts land here."
    return "lo", "Not flagged. Below every v7.1 line."


def features(user, items, oldest, anchor=None):
    """v7.1 feature row for one account. items: slimmed Arctic Shift records. The anchor is the account's last item
    unless given (lookup_parity.py passes the pipeline's matched anchor)."""
    cut = sorted(items, key=lambda x: float(x["created_utc"]))
    anc = float(cut[-1]["created_utc"]) if anchor is None else float(anchor)
    with tempfile.TemporaryDirectory() as d:
        cut_path, grp_path, old_path = (os.path.join(d, f) for f in ("cut.jsonl", "groups.csv", "oldest.json"))
        with open(cut_path, "w", encoding="utf-8") as fh:
            for x in cut:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        with open(grp_path, "w", newline="", encoding="utf-8") as gh:
            w = csv.writer(gh)
            w.writerow(["username", "group", "reasons"])
            w.writerow([user, "lookup", ""])
        with open(old_path, "w") as fh:
            json.dump({user: oldest}, fh)
        try:
            pw = prewindow_features(cut, anc)
        except Exception:
            pw = {}
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            # the salt only hashes the output id inside this temp folder; the project salt is never needed here
            history.score([cut_path], groups=grp_path, out_dir=os.path.join(d, "v71"), salt="lookup", oldest=old_path)
        with open(os.path.join(d, "v71", "accounts.csv"), encoding="utf-8") as fh:
            s = next(csv.DictReader(fh))
    ct = [float(x["created_utc"]) for x in cut]
    row = dict(n_cut=len(cut), hist_age=(anc - ct[0]) / 86400, true_age=(anc - float(oldest)) / 86400 if oldest is not None else None,
               sh=int(bool(hijack.solicit_handle(cut))), sb=int(bool(hijack.solicit_broad(cut))),
               primary=int("primary" in (s["tier"] or "")), tier=s["tier"], flag_list=s["flag_list"])
    for k, v in s.items():
        row.setdefault(k, v)
    for k, v in pw.items():
        row["pw_" + k] = v
    return row


# --- descriptive signals (not inputs to the score) --------------------------------------------------------------
def _text(x):
    return " ".join(str(x.get(k) or "") for k in ("title", "selftext", "body") if (x.get(k) or "").strip() not in REMOVED)


def rhythm(ts):
    hours = collections.Counter(int((t % 86400) // 3600) for t in ts)
    hist = [hours.get(h, 0) for h in range(24)]
    n = len(ts)
    out = dict(hist=hist, n=n)
    if n < MIN_ITEMS:
        out.update(status="too few items")
        return out
    best = min(range(24), key=lambda h: (sum(hist[(h + i) % 24] for i in range(QUIET_HOURS)), h))
    share = sum(hist[(best + i) % 24] for i in range(QUIET_HOURS)) / n
    out.update(quiet_start=best, quiet_share=share)
    if share > NO_RHYTHM:
        out.update(status="no clear rhythm")
        return out
    off = LOCAL_CENTER - (best + QUIET_HOURS / 2)
    off = int(((off + 11) % 24) - 11)
    out.update(status="clear rhythm", offset=off, band=[off - 1, off + 1])
    return out


def describe(user, items):
    subs = collections.Counter(str(x.get("subreddit") or "") for x in items)
    n = len(items)
    us_items = sum(v for k, v in subs.items() if k.lower() in US_SUBS)
    local = [k for k, _ in subs.most_common() if k.lower() in US_PLACES]
    abroad = [[k, OTHER_PLACES[k.lower()]] for k, _ in subs.most_common() if k.lower() in OTHER_PLACES]
    words, en, txt_n = collections.Counter(), 0, 0
    for x in items:
        # curly apostrophes split "don’t" into "don"; fold them to ' first
        t = _text(x).lower().replace("’", "'").replace("‘", "'")
        ws = [w.removesuffix("'s") for w in WORD.findall(t)]
        if not ws:
            continue
        txt_n += 1
        if len(ws) < 4 or any(w in EN_COMMON for w in ws):
            en += 1
        words.update({w for w in ws if w not in STOP and w != user.lower()})
    return dict(top_subs=[[k, v / n] for k, v in subs.most_common(8)], us_share=us_items / n if n else 0,
                local_us=local[:5], local_abroad=abroad[:5], english_share=en / txt_n if txt_n else None,
                keywords=[[k, v / txt_n] for k, v in words.most_common(15)] if txt_n else [])


def analyze(user, raw_items, oldest, M, now=None):
    """Everything the card shows. raw_items: Arctic Shift records (slimmed here). M: the exported model dict."""
    seen, items = set(), []
    for r in raw_items:
        if r.get("author") == user and r.get("id") not in seen:
            seen.add(r.get("id"))
            items.append(slim(r))
    if not items:
        return {"error": "no items"}
    row = features(user, items, oldest)
    p = predict(M, feature_vector(row, M))
    th = M["thresholds"]
    ctl = M["control_scores"]
    tone, text = verdict(p, th)
    ts = [float(x["created_utc"]) for x in items]
    rh = rhythm(ts)
    de = describe(user, items)
    us = de["us_share"] >= US_SHARE
    mismatch = bool(us and rh["status"] == "clear rhythm" and (rh["band"][1] < US_BAND[0] or rh["band"][0] > US_BAND[1]))
    return dict(
        n_items=len(items), n_posts=sum("title" in x for x in items), n_comments=sum("title" not in x for x in items),
        first_item=min(ts), last_item=max(ts),
        age_days=row["true_age"], score=p, rating=rating(p, th), rating_text=rating_text(rating(p, th)), tone=tone, verdict=text, thresholds=th,
        control_pct=sum(c < p for c in ctl) / len(ctl), control_n=len(ctl),
        flag_list=row["flag_list"], tier=row["tier"], solicit_handle=bool(row["sh"]), solicit_broad=bool(row["sb"]),
        default_name=bool(signals.DEFAULT_NAME.match(user)), rhythm=rh, desc=de, us_presenting=us, mismatch=mismatch)
