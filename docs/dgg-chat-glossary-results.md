# DGG live chat glossary: provisional results (scored Nov 9, 2026; predictions in dgg-chat-glossary-predictions.md, unchanged)

## Why this is provisional

The planned data can't be collected. The predictions were written for RustleSearch pulls of the six Reddit weeks
(Aug 18 - Nov 2). RustleSearch caps anonymous use at about 200 requests a day (ops/laptop/README.md: the pull
stopped Nov 2 for that reason), and the six weeks need roughly 45,000 requests (about 110k messages a day, 100 per
page). The study moved to the live logger instead.

So this file scores what it can from the public site's aggregates of the live log
(carrier3rd/dgg-chat-site, data/ as of Nov 9 11:45 UTC): Nov 3-8, six full days, 648,811 messages, 5,024 chatters.
That window includes election night, which is not a normal week. Predictions that need message-level data are left
for a laptop pass over the raw live log. A full pass on the live log should replace this file's numbers, and should
note the window change as a deviation.

Score so far: 2 held, 1 partly held, 2 missed, 4 not yet scorable.

| # | Prediction | Result | Score |
|---|---|---|---|
| 1 | 40%+ of messages contain an emote; 15%+ are emote-only | Emote-only 39.4% of messages (33-44% by day). The "contains an emote" share isn't in the aggregates, but it is at least the emote-only share | **Held** on emote-only; the 40% half is very likely but unverified |
| 2 | Top 20 emotes are over 60% of emote uses | Aggregates count messages per emote for the top 20 only, with no total of emote uses | **Not scorable yet** |
| 3 | Most of the top 10 are laughing, mocking or reaction emotes; approval ranks lower | Top 10: OMEGALUL, hesRight, CINEMA, GIGACHAD, SpeedLaugh, omgBruh, FlawlessVictory, ALARMA, DinkDonk, ShrimpleAs. Laugh/reaction: OMEGALUL, CINEMA, SpeedLaugh, omgBruh, ShrimpleAs (5); alert: ALARMA, DinkDonk; approval/celebration: hesRight (#2), GIGACHAD (#4), FlawlessVictory (#7, election night) | **Partly held**: reaction emotes are half the top 10, but approval ranks high, not low |
| 4 | A third or more of emote messages are inside a combo run | Needs message order | **Not scorable yet** |
| 5 | Median message under 8 words, well below r/Destiny | Median 2-3 words every day | **Held** (r/Destiny side not measured here, but Reddit comments are far longer) |
| 6 | "regarded" and "dear leader" are more common per message in chat than in r/Destiny; "sweeping" mostly an emote | Chat: regarded 0.6, dear leader 7.5 per 10k messages. r/Destiny (data/glossary.csv, rate in the top sub): regarded 86.4, dear leader 14.0 per 10k comments. "sweeping" not in the aggregates | **Missed** on both rates (regarded by over 100x); sweeping not scorable |
| 7 | Chat's top names are the week's on-stream guests; feud names (Pisco, Hutch, Lonerbox) rank lower in chat than in r/Destiny | In the live term list, hutch is the #2 term (10.1 per 10k) and pisco #6 (6.8); lonerbox 1.3. All three are lower per message than in r/Destiny (53.3, 94.2, 19.2), but hutch and pisco lead chat's name terms | **Missed** on rank (provisional: the live term list is curated, not every name) |
| 8 | The biggest day-to-day emote swings line up with stream segments | Needs per-day emote counts and the stream schedule | **Not scorable yet** |
| 9 | The top 1% of chatters write over 25% of lines | Top 50 of 5,024 chatters (1%) wrote 18.7% of messages; the top 100 wrote 29.7% | **Missed** |

## Notes

- Units: chat rates are per 10k messages, Reddit rates per 10k comments, as the predictions framed them. A chat
  message is far shorter, so per-message rates understate chat's word-level use of a term. That doesn't rescue
  prediction 6: "regarded" is rare in chat on any measure.
- The archive scorecard on the site (2014-2020 OverRustle data) answers a different prediction set
  (orl-archive-predictions.md) and is not used here.
- Bots and system lines are dropped in the site's aggregates, per the live pipeline.
