# DGG chat stats

Code, write-ups and the public site for a study of destiny.gg (DGG) chat: a read-only live logger of today's chat,
the 2014-2020 OverRustle archive set against 22 nearby Twitch chats, and an hourly glossary of what chat is saying.

Site: https://carrier3rd.github.io/dgg-chat-site/ (published from the `gh-pages` branch every 15 minutes).

This work started inside the [socialscope](https://github.com/carrier3rd/socialscope) repository and moved here on
Nov 19, 2026, with its git history. socialscope now covers Reddit and Bluesky. **Commit ids cited in `docs/` refer to
socialscope commits**, where each prediction was first committed; the copies of those commits here have different ids.

## What's inside

| Path | What it does |
|---|---|
| `scripts/dgg_live_logger.py` | Read-only logger of DGG's public chat feed (never posts). Runs as the `dgg-live` service. |
| `scripts/dgg_chat_pull.py` | Pulls past days of DGG chat. |
| `scripts/orl_aggregate.py`, `orl_deep.py`, `orl_crossflow.py` | OverRustle archive counts, deep passes and cross-chat flow. |
| `scripts/glossary_count.py`, `scripts/ling.py` | Glossary counts and the shared text features (ling.py is a copy of socialscope's). |
| `site/build_site_data.py`, `site/build_glossary.py` | Build the site's JSON and the hourly glossary. |
| `site/public/` | The site's HTML, JS and CSS. |
| `ops/` | Publish script, systemd units and queue scripts (unit copies; the laptop runs them under systemd --user). |
| `data/` | Glossary CSV, emote list, chat keep-terms. |
| `docs/` | Predictions and results for each DGG study, glossary and emote notes. |

## Ground rules

Predictions are committed before the data they predict is read; results go in a separate file, misses included.
No message text is published, and no one is labeled hostile or harassing by name. Archive chatters stay hashed.
See `CLAUDE.md` for the full rules.
