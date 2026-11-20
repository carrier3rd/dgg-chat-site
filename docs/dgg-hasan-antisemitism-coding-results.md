# Model coding of antisemitism keyword hits, DGG vs Hasan chat, Nov 3-10 2026: results

Predictions: `dgg-hasan-antisemitism-coding-predictions.md` (commit 711746a, Nov 12 10:53 ET, before any coding). Run
Nov 12 on the laptop; script and per-item codes in `~/socialscope_data/as_coding/` (not committed). Aggregates only.

## Data
| | DGG | Hasan |
|---|---|---|
| messages | 714,044 | 1,297,822 |
| keyword candidates (antisemitism + holocaust_distortion) | 299 | 486 |
| by strongest tier | explicit 119, trope 61, dog-whistle 118, contested 1 | explicit 23, trope 111, dog-whistle 344, contested 8 |
| on-topic (Jews/Israel) non-candidates | 2,037 | 7,765 |
| random sample of those, coded | 250 | 250 |

Coders: `claude-opus-5-5` effort low ($4.23) and `claude-fable-5-2` effort high ($13.22), same prompt and schema,
items from both sides shuffled together. 1,285 items, all coded by both, no refusals; every quote was verbatim.

**Confound that dominates the explicit tier:** Twitch AutoMod and channel filters drop messages before delivery, and
public.db leaves out mod-deleted text. DGG has its own filters, which pass the echo, ZOG, "JQ" and slurs. Hasan chat's
near-zero explicit tier is mostly filtering, not proof of a cleaner community.

## Scoring
| # | Prediction | Opus 5.5 | Fable 5.2 |
|---|---|---|---|
| 1 | DGG explicit tier ≥60% joke_or_bait | **miss**: 50.4% (endorse 14.3%) | **hit**: 65.5% (endorse 10.9%) |
| 2 | Endorse share higher in Hasan chat | **miss**: 2.3% vs DGG 7.0% | **miss**: 2.7% vs 5.7% |
| 3 | Hasan trope tier endorse 20-50% | **miss**: 6.3% | **miss**: 7.2% |
| 4 | ≥30% of Hasan trope hits not antisemitic content | **hit**: 89% not | **hit**: 86.5% not |
| 5 | DGG jokes: edgy_shock > mocking_antisemites | **hit**: 66 vs 7 | **hit**: 72 vs 22 |
| 6 | JDA-endorsed per 10k, Hasan ≥ DGG (keyword candidates) | **miss**: 0.05 vs 0.28 | **miss**: 0.03 vs 0.22 |
| 7 | On-topic miss sample <3% endorse on both sides | **miss**: DGG 1.6%, Hasan 3.2% | **hit**: 0.8%, 2.4% |
| 8 | Stance agreement ≥75% and kappa(endorse) ≥0.6 | **hit**: 87.2%, kappa 0.64 (stance kappa 0.60, content kappa 0.78) | |
| 9 | Fable ≥10% fewer endorse than Opus | **hit**: 38 vs 45 (16% fewer) | |

Opus: 3 hits of 7, Fable: 4 of 7; pair: 2 of 2.

## What the coding shows
- **Most "trope" keyword hits are false alarms on both sides.** "Globalist", Soros, "Israel lobby", the "109" code and
  the Jewish-politician imagery patterns are about 75-97% not_applicable on both models. The equal trope rate in the
  keyword comparison was mostly noise.
- **DGG: explicit codes, mostly edgy irony, with a sincere minority.** 73-85% of DGG explicit hits are antisemitic
  content in any tone (echo, ZOG, "the JQ", "joo" spellings). Both models code most of these as joke_or_bait of the
  edgy_shock kind (using the code for shock or in-group humour, not mocking antisemites). 11-14% are coded sincere.
  In the item contexts, these come in pile-ons: runs of echoes and ZOG with PEPE emotes, aimed at politicians, donors
  and "the media".
- **Hasan chat: a different form, rarely joking, mostly outside the keywords.** Endorsed items are dual-loyalty and
  "Israel controls US politicians" claims ("Israel-firsters", "agents of Israel", serving Israeli "masters", Israel
  installing officials), dual-loyalty charges at Jewish journalists, and Holocaust inversion ("committing a holocaust
  in Gaza", "Zionism is Nazism"). The inversion items are IHRA-only (JDA: contested, not antisemitic on their face).
  **The control and dual-loyalty items count as antisemitic under both definitions**: the JDA, too, treats the
  Jewish-control trope applied to Israel ("Israel controls the US government/military/media") and dual-loyalty charges
  as antisemitic. That differs from criticism of documented lobbying (AIPAC money), which both models mostly coded
  not_applicable (34-35 of 35 "Israel lobby" hits). Joking is rare (0.8-1.9% of candidates).
  Scaled from the on-topic sample, this sincere control/dual-loyalty talk is roughly 100-250 messages in this week of
  Hasan chat (JDA, both models' range) vs about 30-50 sincere items of any kind in DGG.
- **The keywords miss Hasan chat's form.** In the on-topic sample, 2.4-3.2% of Hasan messages are endorsed
  antisemitism vs 0.8-1.6% in DGG. Scaled to the on-topic pool, adding misses gives an endorsed JDA-antisemitic rate of
  about 0.75-1.7 per 10k messages in Hasan chat vs 0.45-0.74 in DGG. That reverses prediction 6, but it is post hoc,
  and the intervals overlap (Hasan JDA 0.28-3.4, DGG 0.29-1.4 across the two models' CIs). A larger on-topic sample
  is needed before claiming a difference.
- **Sincere content is rare in both chats.** Point estimates including misses are 0.45-2.2 endorsed antisemitic
  messages (IHRA) per 10k, about 1 in 4,500 to 1 in 22,000 messages.

## The two coders
- Fable is more willing to call DGG explicit hits jokes (65.5% vs 50.4%) and to use condemn and mocking_antisemites
  (22 vs 7). Opus uses unclear far more (40 items Fable called not_applicable).
- The main disagreements: Opus endorse vs Fable joke_or_bait on 10 items, and joke_or_bait vs not_applicable on 37.
  Sincerity in shock-humour pile-ons is where the models disagree, as expected.
- Neither model is ground truth. Next step: a blind hand-check of about 100 items, oversampling disagreements
  (`rhetoric.py sheet`-style), then a larger on-topic sample (around 1,000 per side) to tighten the miss estimate.

## Addendum, Nov 19 2026: 1,000 new on-topic messages per side, Opus only

Predictions 10-14 (addendum in the predictions file, commit d2b1548, written before drawing or coding). New random
sample, seed 20261119, Nov 12 items removed (159 DGG, 48 Hasan) before 1,000 per side were kept. `claude-opus-5-5`
effort low, Nov 12 prompt and schema. 2,000 of 2,000 coded; 1,996 quotes verbatim. Cost $6.48 (limit $15).

| | DGG | Hasan |
|---|---|---|
| Endorsed antisemitism (endorse + antisemitism/holocaust_distortion) | 21 = 2.1% (1.4-3.2%) | 35 = 3.5% (2.5-4.8%) |
| of which JDA-antisemitic | 20 | 22 |
| antisemitic_content true | 127 | 49 |
| of those, joke_or_bait | 84 (66%) | 7 (14%) |
| stance unclear | 99 | 24 |

| # | Prediction | Result |
|---|---|---|
| 10 | Hasan 1.5-5%, DGG 0.5-3% | **Hit** (3.5%, 2.1%) |
| 11 | Hasan share higher | **Hit** |
| 12 | 95% interval for Hasan minus DGG excludes zero | **Miss**: +1.40 points, Newcombe -0.06 to +2.91 |
| 13 | At least half of Hasan endorsed items JDA-antisemitic | **Hit** (22 of 35) |
| 14 | Joke share of antisemitic content higher in DGG | **Hit** (66% vs 14%) |

4 of 5 hit. The sign of the Nov 12 result holds on new messages, but the share difference stops just short of clear.

**What the endorsed items are.** Hasan: 28 of 35 carry both antisemitism and israel categories; the most common
patterns are Zionist control (16), dual loyalty (12, both forms) and Jewish control (6), with 3 Gaza-Holocaust
inversions; most target "Israel or Zionists" (23). DGG: mostly antisemitism alone (18 of 21), most often Jewish
control (7), aimed at Jews (10) or named people (5). "Zionist control" items are JDA-contested by definition, which is
why Hasan's JDA count (22) trails its endorse count more than DGG's.

**Rate per message (not predicted; post hoc).** Hasan chat has about twice as many on-topic messages per message as
DGG (7,765 of 1.30M vs 2,037 of 714k). Scaling the JDA-endorsed share to each pool gives about 171 missed messages in
Hasan chat that week (113-257) vs 41 in DGG (26-63): 1.32 vs 0.57 per 10k messages, intervals 0.87-1.98 and 0.36-0.88.
Combined with the keyword candidates this supports the Nov 12 reading, but it was not a pre-stated test.

Caveats as on Nov 12: one model, no hand check, Twitch filtering removes explicit content from Hasan chat before it
is logged, and DGG's high unclear count (99) leaves room for sincerity the model would not commit to.
