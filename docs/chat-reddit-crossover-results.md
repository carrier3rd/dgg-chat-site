# Chat-to-Reddit language crossover: results (Nov 3, 2026)

Predictions: docs/chat-reddit-crossover-predictions.md (committed before any chat token file was opened).
Data: OverRustle token counts by year for destiny.gg chat (2013-Apr 2020, 110M messages), Destiny's Twitch chat,
Vaush, H3h3productions, Hutch, Asmongold, Moistcr1tikal and Rajjpatel; against the glossary's 2026 Reddit counts.

## A measurement problem found first
The aggregator drops any token that equals some chatter's nick, to keep names out of the output. With millions of
nicks, that also deletes ordinary words: "the" and "based" are 0 in destiny.gg chat. So a count above zero is real,
but a zero means "absent, or someone used it as a nick." Two-word phrases ("dear leader", "blue maga") were never
counted. Fix committed: `--keep-file data/chat_keep_terms.txt` keeps the 81 glossary terms through the nick filter
and counts multi-word phrases into phrases.tsv. It needs a rerun on the laptop.

## Scoring
1. **Consistent, not proven.** pestiny, sexpestiny, slopulism, omnicause, campist, glizzy, gwam, tamara, hasbara and
   vatnik are zero in every channel, but zeros are not trustworthy until the rerun.
2. **Partly held.** "dggers" is in destiny.gg chat by 2018 and reaches 8.1 per 100k messages in 2020. "based" is
   unscorable in site chat (nick filter) but runs 60 per 100k in Destiny's Twitch chat and 448 in Vaush's.
3. **Unscorable.** "dear leader" is a phrase and was not counted. Waits for the rerun.
4. **Held, with the same caveat.** Hutch is in destiny.gg chat from 2018 (23 per 100k in 2020). Lonerbox is zero.
5. **Missed.** 7 of destiny.gg chat's 50 most distinctive tokens are elevated 3x or more among r/Destiny regulars
   (destiny, pepe, yee, omegalul, soy, melina, amazin), short of 10. Most distinctive chat tokens are emotes
   (PepeLaugh, FeelsWeirdMan, monkaS, DuckerZ) that do not get typed into Reddit comments.
6. **Weak hold.** 4 of the 7 crossover tokens are also among Destiny's Twitch chat top 200. The test is close to
   circular, so it carries little weight.

## What it adds to the glossary
- Chat-era dating for lefties (2019 surge), dggers (2018+), regarded (barely in chat before 2020, while the plain
  r-word was common), chud and libs (left-chat words first, heavy in Vaush's chat), Hutch, Kulinski and Mouton.
- "sweeping" is an official destiny.gg emote, confirming the owner's note.
- Five crossover emotes typed in r/Destiny comments: soy, amazin, yee, pepe, omegalul.

## Rerun (laptop)
Channels: Destinygg, Destiny, Vaushgg, H3h3productions, Hutch. Output to a new folder so the DONE markers do not skip:
`python3 -I scripts/orl_aggregate.py --archive "$HOME/Downloads/OverrustleLogs Archive" --out ~/socialscope_data/orl_agg_keep --salt-file ~/socialscope/.socialscope_salt --emotes ~/socialscope_data/dgg_chat/emotes.json --progress-dir ~/socialscope_data/orl_progress_keep --keep-file ~/socialscope/data/chat_keep_terms.txt --channels Destinygg Destiny Vaushgg H3h3productions Hutch`
