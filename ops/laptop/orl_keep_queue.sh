#!/bin/bash
# orl_aggregate rerun with --keep-file (data/chat_keep_terms.txt) for 5 channels, into orl_agg_keep.
# Keep terms survive the nick filter; multi-word terms are counted into phrases.tsv. Progress: orl_progress_keep.
D=$HOME/socialscope_data
nohup "$D/status.sh" > "$D/status_loop.out" 2>&1 &
echo "orl_keep start $(date)"
cd "$HOME/socialscope" && python3 -I scripts/orl_aggregate.py --archive "$HOME/Downloads/OverrustleLogs Archive" \
  --out "$D/orl_agg_keep" --salt-file "$HOME/socialscope/.socialscope_salt" --emotes "$D/dgg_chat/emotes.json" \
  --progress-dir "$D/orl_progress_keep" --keep-file "$HOME/socialscope/data/chat_keep_terms.txt" \
  --channels Destinygg Destiny Vaushgg H3h3productions Hutch
rc=$?
echo "orl_keep end $(date) rc=$rc"
