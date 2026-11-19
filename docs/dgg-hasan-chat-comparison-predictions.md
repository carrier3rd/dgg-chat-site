# DGG chat vs Hasan chat, Nov 3-10 2026: predictions

Written Nov 12, 2026 (laptop/Windows conductor session), **before any DGG live-chat message was read for this study**.
Never edit this list; additions go at the end as dated addenda. Results go in `dgg-hasan-chat-comparison-results.md`.

What I had already seen, so these are not blind on that side: aggregate stats of Hasan's chat (thehasanproject
public.db, Aug 10 - Nov 10: ~12k chatters/stream, ~255 msgs/min, emote-heavy, Destiny nicknames), and the earlier
DGG glossary results (`dgg-chat-glossary-results.md`). I have not looked at the dgg_live files beyond their names
and sizes.

## Data and plan
- DGG: `~/socialscope_data/dgg_live/2026-11-03 .. 2026-11-10` (live logger, all messages, raw nicks + hash).
- Hasan: thehasanproject public.db chat for streams dated 2026-11-03 .. 2026-11-10 (Twitch replays + live logger;
  Nov 9 is known to be partial). Deleted text is not in public.db and is excluded on both sides where flagged.
- Same tokenizer and lexicons on both sides. Topic lexicon = the one used for the Hasan trend survey (Israel/Palestine,
  Trump, Democrats, elections, Mamdani/NYC, ICE, economy, Ukraine/Russia, China, Iran), plus cross-mentions
  (Hasan names in DGG; Destiny names and nicknames in Hasan chat), plus thehasanproject research/watchlist.csv.
- Aggregates only. No per-person labels; nicks are not printed in results.

## Predictions
1. **Length.** DGG's median message is at least 2x as many words as Hasan chat's.
2. **Reaction share.** Messages of 1-2 tokens are at least 1.5x as common in Hasan chat as in DGG.
3. **Size and concentration.** DGG has under 1/5 of Hasan chat's distinct chatters per day, and its top 1% of
   chatters write at least 2x the share of messages that Hasan chat's top 1% write.
4. **Talking to each other.** Messages that address another chatter (DGG: starts with or contains a nick that chatted
   that day; Twitch: @mention of a non-streamer) are at least 3x as common in DGG.
5. **Cross-attention asymmetry.** DGG chat mentions Hasan (hasan, piker, hassan, hasanabi) at a per-10k-message rate at
   least 10x Hasan chat's rate for Destiny (name, dgg, bonnell and the nicknames epstiny, sexpest(iny), pestiny).
6. **Israel/Palestine.** DGG's per-10k-message rate is at least as high as Hasan chat's.
7. **Election week.** Both chats' election/Democrat rates peak on Nov 3 or Nov 4.
8. **Profanity** (fixed small list) is within 1.5x between the two.
9. **Vocabulary.** Jaccard overlap of the two chats' top 300 non-stopword tokens (by distinct chatters) is under 0.25.
10. **Hostility vocabularies point in opposite directions.** Watchlist anti_liberal hits are at least 3x higher per
    10k in Hasan chat; this fixed anti-left list is at least 3x higher per 10k in DGG:
    `tankies?|commies?|hamas (supporter|simp|lover)s?|terrorist (sympathizer|supporter)s?|pro-?hamas|hamasabi|`
    `hezbollah (simp|lover)s?|stalinists?|maoists?|useful idiots?|pinkos?|commie scum|red fash|leftoids?|leftists? (are|is) (regarded|retarded|stupid)`.
11. **Antisemitism keyword hits** (watchlist category antisemitism, all tiers) are higher per 10k in Hasan chat.

## Scoring
Each prediction is hit or miss on the stated threshold, reported with the numbers. Keyword measures are only
keyword measures: no model coding in this study.
