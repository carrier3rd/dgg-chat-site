#!/bin/bash
# Rebuild the public DGG chat stats site and push it to its GitHub Pages repo.
# Only aggregates are published (see site/build_site_data.py). Run every 15 minutes by dgg-site.timer.
set -euo pipefail
REPO="$HOME/socialscope"
SITE="$HOME/dgg-chat-site"          # local clone of the public Pages repo
[ -d "$SITE/.git" ] || { echo "missing $SITE clone"; exit 1; }
rsync -a --delete --exclude data/ --exclude .git/ --exclude CNAME "$REPO/site/public/" "$SITE/"
mkdir -p "$SITE/data"
cp "$REPO/site/public/data/scorecard.json" "$SITE/data/"
python3 -I "$REPO/site/build_site_data.py" --out "$SITE/data" --skip-archive
cd "$SITE"
git add -A
if git diff --cached --quiet; then echo "site: no changes"; exit 0; fi
git commit -q -m "Data update $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q
echo "site: pushed $(date -u +%FT%TZ)"
