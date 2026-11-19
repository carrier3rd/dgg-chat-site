#!/bin/bash
# Aggregates the OverRustle archive (12 channel .7z files, smallest first) into hashed count tables in orl_agg.
# Progress goes to orl_progress/progress.json (served on :8766); the script's own output lands in this queue's .out.
D=$HOME/socialscope_data
nohup "$D/status.sh" > "$D/status_loop.out" 2>&1 &
echo "orl start $(date)"
cd "$HOME/socialscope" && python3 -I scripts/orl_aggregate.py --archive "/home/probs/Downloads/OverrustleLogs Archive" \
  --out /home/probs/socialscope_data/orl_agg --salt-file /home/probs/socialscope/.socialscope_salt \
  --emotes /home/probs/socialscope_data/dgg_chat/emotes.json --progress-dir /home/probs/socialscope_data/orl_progress
rc=$?
echo "orl end $(date) rc=$rc"
