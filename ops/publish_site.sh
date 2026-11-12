#!/bin/bash
# Rebuild the public DGG chat stats site and push it to its GitHub Pages repo.
# Aggregates, plus DGG handles in live_chatters.json since Nov 5 2026 (see site/build_site_data.py). Run every 15 minutes by dgg-site.timer.
set -euo pipefail
REPO="$HOME/socialscope"
SITE="$HOME/dgg-chat-site"          # local clone of the public Pages repo
[ -d "$SITE/.git" ] || { echo "missing $SITE clone"; exit 1; }
rsync -a --delete --exclude data/ --exclude .git/ --exclude CNAME "$REPO/site/public/" "$SITE/"
# Version-tag app.js and style.css so browsers pick up new code at once (Pages caches them for 10 minutes; the
# tag changes only when the files do). Added Nov 5 2026 after a cached app.js hid the new top-chatters table.
v=$(cat "$SITE/app.js" "$SITE/style.css" | sha1sum | cut -c1-8)
sed -i "s#href=\"style.css\"#href=\"style.css?v=$v\"#; s#src=\"app.js\"#src=\"app.js?v=$v\"#" "$SITE/index.html"
mkdir -p "$SITE/data"
cp "$REPO/site/public/data/scorecard.json" "$SITE/data/"
python3 -I "$REPO/site/build_site_data.py" --out "$SITE/data" --skip-archive
# Bots tab (Nov 11 2026): confirmed bot finds, rewritten every run so a reversed listing comes off at once.
python3 -I "$REPO/scripts/botfinds/build_site_bots.py" --out "$SITE/data"
cd "$SITE"
git add -A
if git diff --cached --quiet; then echo "site: no changes"; exit 0; fi
git commit -q -m "Data update $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q
echo "site: pushed $(date -u +%FT%TZ)"
