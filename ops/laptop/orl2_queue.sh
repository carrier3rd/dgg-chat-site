#!/bin/bash
# Second orl_aggregate pass: reruns the first pass's command (launched by hand once the first had finished;
# the old pgrep wait loop matched a leftover shell and never exited, so it is gone).
# Channels with orl_agg/<channel>/DONE are skipped, so this only redoes channels that errored or never finished.
# Shares orl_progress/progress.json with the first pass (the page on :8766 shows whichever pass ran last);
# the first pass's final progress.json is kept as orl_pass1_progress.json.
D=$HOME/socialscope_data
nohup "$D/status.sh" > "$D/status_loop.out" 2>&1 &
echo "orl2 start $(date)"
cd "$HOME/socialscope" && python3 -I scripts/orl_aggregate.py --archive "/home/probs/Downloads/OverrustleLogs Archive" \
  --out /home/probs/socialscope_data/orl_agg --salt-file /home/probs/socialscope/.socialscope_salt \
  --emotes /home/probs/socialscope_data/dgg_chat/emotes.json --progress-dir /home/probs/socialscope_data/orl_progress
rc=$?
echo "orl2 end $(date) rc=$rc"
