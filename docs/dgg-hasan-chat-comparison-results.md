# DGG chat vs Hasan chat, Nov 3-10 2026: results

Predictions: `dgg-hasan-chat-comparison-predictions.md` (commit 2a1672d, Nov 12 09:20 ET, before the DGG data was
read). Run Nov 12 2026 on the laptop; script kept at `~/socialscope_data/dgg_hasan_compare.py`, output
`~/socialscope_data/dgg_hasan_compare.json` (aggregates; not committed). Keyword measures only, no model coding.

## Data
| | DGG (live logger) | Hasan (Twitch replays + live logger) |
|---|---|---|
| messages | 714,044 | 1,298,336 |
| distinct chatters | 5,126 | 81,896 |
| chatters per day | 1,285-3,760 (median ~2,200) | 14,350-57,981 (Nov 9 partial: 2,323) |
| messages per chatter | 139 | 16 |

**Read every comparison with these confounds in mind:**
- **Filtering happens before the data exists, and differently.** Twitch AutoMod and Hasan's channel filters remove
  messages before they are delivered, so neither the replays nor the logs contain them. DGG's filters are its own and
  evidently pass terms Twitch blocks ("retarded": 845 DGG chatters vs about 0 in Hasan chat; the triple-parenthesis
  "echo": 79 vs 0).
- DGG chat runs 24/7; Hasan chat exists only while he streams.
- Hasan's replays include bot and subscription-notice lines ("subscribed" from 10k accounts). Those inflate his top-1% share.
- Words that equal any chatter's name were dropped from the word lists (privacy), which removes a few real words.

## Scoring
| # | Prediction | Result | Numbers |
|---|---|---|---|
| 1 | DGG median message ≥2x Hasan's words | **miss** (reversed) | median 2 vs 3 words; mean 4.4 vs 5.0 |
| 2 | 1-2 token messages ≥1.5x more common in Hasan | **miss** (reversed) | 53.8% DGG vs 43.8% Hasan |
| 3a | DGG under 1/5 of Hasan's chatters per day | **hit** | ~1/7 to 1/22 |
| 3b | DGG top 1% share ≥2x Hasan's | **miss** (reversed) | 19.4% vs 36.3% (Hasan side inflated by bots/notices); top 10%: 69.8% vs 76.2% |
| 4 | Addressing another chatter ≥3x more in DGG | **miss** (right direction) | 5.45% vs 3.38% (1.6x) |
| 5 | DGG→Hasan mentions ≥10x Hasan→Destiny | **hit** | 44.4 vs 1.4 per 10k (32x); Destiny's name is filtered in Hasan chat |
| 6 | Israel/Palestine DGG ≥ Hasan | **miss** | 21.1 vs 59.5 per 10k |
| 7 | Election/Democrat rates peak Nov 3-4 in both | **partial** | elections peak Nov 3 in both; Democrats peak Nov 4 in DGG but Nov 5 (full days) in Hasan |
| 8 | Profanity within 1.5x | **hit** | 322.5 vs 345.7 per 10k |
| 9 | Top-300 vocabulary Jaccard < 0.25 | **miss** | 0.446 |
| 10a | anti_liberal ≥3x in Hasan | **miss** (narrow) | 9.93 vs 3.49 per 10k (2.8x) |
| 10b | anti-left list ≥3x in DGG | **miss** | 6.1 vs 4.8 per 10k (1.3x) |
| 11 | Antisemitism keyword hits higher in Hasan | **miss** | 0.88 vs 2.48 per 10k; see below |

3 hits, 1 partial, 9 misses. My model of DGG chat as long-form arguing was wrong for this week: both chats are mostly
short reactions, and DGG's are shorter.

## Antisemitism keywords, by pattern
DGG's higher total is almost all **explicit-tier terms that Twitch filters**: echo `(((...)))` 79, ZOG 11, slur 8,
"kill jews" 8, "jewish question" 5 (Hasan chat: 3 explicit hits in total). Many DGG snippets read as ironic or meme-like
("(((they))) SCHEMING", "PEPE ZOG ZOG"), but irony was not coded. **Trope-tier** terms, which filters mostly
miss, are about equal per message: DGG ~0.87 vs Hasan ~0.85 per 10k. The mix differs: in Hasan chat, globalist 37,
Soros 31, dual loyalty 23, blood libel/adrenochrome 12 and 6MWE 16. Also in Hasan chat: "liberal_democracy_contempt"
156 vs 4. Coding these with the rhetoric method is the next step before any claim about either community.

## Topics (per 10k messages)
Hasan chat is more topical on every politics line we measured except Ukraine/Russia: Democrats 150 vs 72,
elections 194 vs 118, Trump 111 vs 65, Israel/Palestine 60 vs 21, Mamdani/NYC 26 vs 3, economy 19 vs 11,
ICE 14 vs 9, Iran 11 vs 6, China 14 vs 11; Ukraine/Russia 3 vs 10. Part of this is the 24/7 DGG chat diluting its rate.

## Vocabulary
- Shared everyday core (Jaccard 0.45): "omegalul", "ripbozo", "trump", "hasan", "people", profanity.
- The most distinctive words on each side are mostly the platform's own emotes.
- Mirror pattern in "-stiny" words: DGG uses them for its streamer (godstiny, blesstiny, cutestiny, sweatstiny,
  painstiny, ditchstiny), while Hasan chat uses them as insults (epstiny, pestiny, sexpestiny).
- DGG-only: "retarded"/"retard" (filtered on Twitch), "schizo", "soypoint", "cuckcrab".
- Hasan-only: "libbers", "wokege", "toobased", "boomies", "haschud", "transgenderpride", "hasraid".
