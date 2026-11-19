# CLAUDE.md

DGG chat work moved here from the socialscope repo on Nov 19, 2026 (see README.md). The rules below are socialscope's,
kept for this repo. Data still lives in `~/socialscope_data/` (dgg_live, dgg_chat, orl_agg, glossary state), and the
HMAC salt is still `~/socialscope/.socialscope_salt`, so hashes match across both repos. Never commit or print the salt.

## Layout on the laptop

- `~/dgg-chat-site`: this repo, `main` branch = source.
- `~/dgg-chat-site-pages`: a git worktree of the `gh-pages` branch = the published site. `ops/publish_site.sh` builds
  into it and pushes. GitHub Pages serves `gh-pages`.

## Rules

1. **Never discard uncommitted work.** Run `git status` and `git diff` before any checkout, reset, stash or restore.
   Uncommitted changes may be another session's work. Commit it or ask; don't discard it.
2. **Commit promptly,** in small commits by topic, and push.
3. **Predictions are timestamped records.** Commit a `*-predictions.md` file before running or reading the data it
   predicts. Never edit an existing prediction; additions go at the end as dated addenda. Results go in a separate
   `*-results.md` file, misses included.
4. **Fix bugs in place** with a short comment saying what was wrong and when, and read a script's current contents
   before editing it.
5. **Privacy.** Since Nov 5 2026 (the owner's decision) DGG chat nicks are kept raw: the live logger stores "nick" next
   to the hash "u" (HMAC-SHA256 with the salt above, first 16 hex chars), and the site shows DGG handles in its chatter
   tables (message counts and activity only). Still in force: never print the salt; archive (2014-2020) chatters stay
   hashed; chat accounts are never linked to Reddit accounts or to real-world identities; no per-person hostility, raid
   or harassment labels are published; no message text is published; private sample files (samples_*.jsonl) are never
   committed or published. This repo is public and its `gh-pages` branch is the live site: nothing from
   `~/socialscope_data/` goes in except the aggregate JSON the build scripts write.
6. **Long jobs.** Every long job runs under nohup with systemd-inhibit, uses absolute paths, gets a line in
   `~/socialscope_data/jobs.tsv`, and writes progress where status.sh can see it. Wait loops use a PID file or a
   pattern anchored to the start of the command line (see socialscope's CLAUDE.md rule 6 for why).
7. **Servers serve only status folders** (`python3 -m http.server --directory <dir>`), never a data folder. Ports:
   8765 dgg_progress, 8766 orl_progress, 8767 dgg_live_status.
8. **Standing service: dgg-live** (systemd --user, unit copy in `ops/laptop/dgg-live.service`). Restart it after any
   change to `scripts/dgg_live_logger.py`, then check that status.json shows plausible messages per minute and far
   fewer distinct users than messages. Timers: `dgg-site.timer` (publish every 15 min), `dgg-glossary.timer` (hourly).
9. **Say how jobs ended** in STATUS.txt and jobs.tsv (done / stopped / failed, and why).
