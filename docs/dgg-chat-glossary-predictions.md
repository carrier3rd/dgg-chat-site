# DGG live chat glossary: predictions (written Nov 2, 2026, before any chat data was read)

Side study. Source: destiny.gg chat logs via rustlesearch.dev. Goal: a glossary of emotes and chat slang,
same format as docs/glossary.md, to describe DGG as a community. Not used for bot detection or coordination claims.

## Plan
- Window: the same weeks as the Reddit pulls (Aug 18, Sep 8, Sep 22, Oct 13, Oct 20, Oct 27) so chat and r/Destiny
  can be compared over the same events.
- Emote vocabulary: the official destiny.gg emote list, so emotes are matched against a fixed list and not guessed.
- Usernames: hashed with the project salt at ingest. No nick is printed, committed or used to link chat accounts to
  Reddit accounts.
- Bot and system lines (chat bot, mod commands, sub announcements) are dropped before counting.
- Measures: share of messages that contain an emote, emote frequency and rank, emote-only messages, combos
  (runs of the same emote in a short window), and Fightin' Words log-odds of chat vs r/Destiny comments for the
  non-emote vocabulary.

## Predictions
1. Emotes are dense. At least 40% of chat messages contain one, and at least 15% are emote-only.
2. Heavy concentration. The top 20 emotes account for over 60% of emote uses (Zipf-like tail).
3. Laughter and reaction emotes lead. Most of the top 10 are laughing, mocking or reaction emotes
   (PepeLaugh-style, LUL-style, YEE, OMEGALUL-style). Expressions of approval rank lower.
4. Combos are a large share of emote uses: at least a third of emote messages fall inside a combo run.
5. Messages are short. Median message length is under 8 words, well below r/Destiny comments.
6. The Reddit glossary carries over. "regarded" and "dear leader" appear in chat at higher rates per message than in
   r/Destiny; "sweeping" shows up mainly as an emote or reaction, not in the "sweeping for X" form.
7. Chat names differ from Reddit names. Chat's top non-emote names are the people on stream that week (debate
   guests, panel members); the long-running Reddit feud names (Pisco, Hutch, Lonerbox) rank lower in chat than in
   r/Destiny.
8. Emote usage is event-driven. The single biggest day-to-day swings in a few emotes line up with specific stream
   segments, and the same emotes are quiet on off days.
9. A small share of chatters write most messages: the top 1% of hashed accounts write over 25% of lines.

## Scoring
Each prediction is scored held / partly held / missed in the results file, misses included.
