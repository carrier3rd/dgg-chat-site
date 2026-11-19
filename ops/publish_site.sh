#!/bin/bash
# Rebuild the public DGG chat stats site and push it to this repo's gh-pages branch.
# Aggregates, plus DGG handles in live_chatters.json since Nov 5 2026 (see site/build_site_data.py). Run every 15 minutes by dgg-site.timer.
# Nov 19 2026: moved here from the socialscope repo. Source is ~/dgg-chat-site (main); the published site is the
# gh-pages worktree ~/dgg-chat-site-pages. The Bots and Lookup tabs moved to the socialscope site.
set -euo pipefail
REPO="$HOME/dgg-chat-site"
SITE="$HOME/dgg-chat-site-pages"    # git worktree of the gh-pages branch
[ -d "$SITE" ] || { echo "missing $SITE (git -C $REPO worktree add $SITE gh-pages)"; exit 1; }
rsync -a --delete --exclude data/ --exclude .git --exclude CNAME "$REPO/site/public/" "$SITE/"
# Version-tag app.js and style.css so browsers pick up new code at once (Pages caches them for 10 minutes; the
# tag changes only when the files do). Added Nov 5 2026 after a cached app.js hid the new top-chatters table.
v=$(cat "$SITE/app.js" "$SITE/style.css" | sha1sum | cut -c1-8)
sed -i "s#href=\"style.css\"#href=\"style.css?v=$v\"#; s#src=\"app.js\"#src=\"app.js?v=$v\"#" "$SITE/index.html"
mkdir -p "$SITE/data"
rm -f "$SITE/data/botfinds.json"
cp "$REPO/site/public/data/scorecard.json" "$SITE/data/"
python3 -I "$REPO/site/build_site_data.py" --out "$SITE/data" --skip-archive
cd "$SITE"
git add -A
if git diff --cached --quiet; then echo "site: no changes"; exit 0; fi
git commit -q -m "Data update $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q origin gh-pages
echo "site: pushed $(date -u +%FT%TZ)"
