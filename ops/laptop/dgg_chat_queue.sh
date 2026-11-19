#!/bin/bash
# Pulls destiny.gg chat (6 Reddit weeks, 42 UTC days) into ~/socialscope_data/dgg_chat with the local laptop salt.
# dgg_chat_pull.py appends its progress to ~/socialscope_data/STATUS.txt, which status.py replaces every 60 s,
# so it runs with HOME pointed at dgg_chat_home: its lines land in dgg_chat_home/socialscope_data/STATUS.txt,
# which status.py reads as this job's log. --out and --salt-file are absolute, so nothing else moves.
D=$HOME/socialscope_data
nohup "$D/status.sh" > "$D/status_loop.out" 2>&1 &
echo "dgg_chat start $(date)"
cd "$HOME/socialscope" && HOME="$D/dgg_chat_home" python3 -I scripts/dgg_chat_pull.py \
  --out "$D/dgg_chat" --salt-file "$HOME/socialscope/.socialscope_salt" \
  --progress-dir /home/probs/socialscope_data/dgg_progress > "$D/dgg_chat_run.log" 2>&1
rc=$?
echo "dgg_chat end $(date) rc=$rc"
