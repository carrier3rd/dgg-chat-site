# Model coding of antisemitism keyword hits, DGG vs Hasan chat, Nov 3-10 2026: predictions

Written Nov 12, 2026, **before any message was sent to a model for this study**. Never edit this list; additions go at
the end as dated addenda. Results go in `dgg-hasan-antisemitism-coding-results.md`.

Follows `dgg-hasan-chat-comparison-results.md` (keyword counts only). What I have already seen, so these are not blind:
the per-pattern keyword counts on both sides, and up to 3 DGG snippets for each of the 6 most frequent antisemitism
pattern ids (several read as ironic memes: "(((they))) SCHEMING", "PEPE ZOG ZOG"). I have read no Hasan-chat
antisemitism snippets.

## Data and method
- Same windows as the comparison: DGG live logger 2026-11-03..10 (714k messages); Hasan chat in thehasanproject
  public.db for streams dated 2026-11-03..10 (1.30M messages, mod-deleted text excluded; Nov 9 partial).
- **Candidates:** every message matching a thehasanproject `rhetoric.py` pattern (watchlist.csv + the Allen
  dog-whistle glossary, `needs_context` entries only when the message also mentions Jews or Israel) in categories
  `antisemitism` or `holocaust_distortion`.
- **Miss sample:** 250 random non-candidate messages per side that hit the `topic_jews`/`topic_israel` patterns.
- **Context:** the 10 messages before each one in the same chat, authors replaced by per-item aliases; @mentions and
  words equal to a chatter's name masked. No stream transcript on either side (DGG has none), so context is symmetric.
- **Blinding:** items from both sides are shuffled together; the prompt does not say which community a message is from
  (emotes will often reveal it).
- **Coders:** the same prompt and schema on two models, as Message Batches:
  `claude-opus-5-5` at effort low (the rhetoric study's setting) and `claude-fable-5-2` at effort high.
- **Fields:** antisemitic_content (uses a slur, code, trope or Holocaust distortion, whatever the tone); stance
  (endorse / joke_or_bait / quote_or_report / condemn / unclear / not_applicable); irony_kind (none / edgy_shock /
  mocking_antisemites / unclear); target; IHRA and JDA flags (false unless endorse); verbatim quote, checked.
- Aggregates only. No per-person labels, no names in outputs; per-item codes stay in `~/socialscope_data/as_coding/`.

## Predictions (scored on each model separately)
1. **DGG explicit tier is mostly irony.** Of DGG candidates whose strongest hit is `explicit`, at least 60% are coded
   joke_or_bait.
2. **Hasan chat is more sincere.** The endorse share among all candidates is higher in Hasan chat than in DGG.
3. **Hasan trope tier is mixed.** Of Hasan candidates whose strongest hit is `trope`, the endorse share is between
   20% and 50%.
4. **Many Hasan trope hits are not about Jews.** At least 30% of Hasan trope-tier candidates are coded
   antisemitic_content = false.
5. **DGG irony is edgy, not anti-antisemite.** Among DGG joke_or_bait candidates, edgy_shock outnumbers
   mocking_antisemites.
6. **Rate.** Endorsed messages that are JDA-antisemitic, per 10k messages, are at least as high in Hasan chat as in DGG.
7. **Keywords miss little.** In each side's on-topic miss sample, under 3% are coded endorse with an antisemitism or
   holocaust_distortion category.
8. **Coders agree.** Opus and Fable give the same stance on at least 75% of items; Cohen's kappa on endorse-or-not is at
   least 0.6. (Scored once, on the pair.)
9. **The higher model is more cautious.** Fable codes at least 10% fewer endorse items than Opus (relative). (Scored
   once.)

## Scoring
Each prediction is hit or miss on its threshold, reported with the numbers, for each model where it applies. Neither
model is ground truth; disagreements are reported, not resolved. A hand-checked sample would be the next step.

## Addendum, Nov 19 2026: a larger on-topic sample, Opus only (written before any new item is drawn or coded)

The Nov 12 results (`dgg-hasan-antisemitism-coding-results.md`) found that most endorsed antisemitism in Hasan chat
sits outside the keywords, and that adding those misses put Hasan chat above DGG, but post hoc, from 250 on-topic
messages per side, with overlapping intervals. This addendum tests that on new messages.

- **Sample:** a new random sample of 1,000 on-topic non-candidates per side (same week, same definition, same masking,
  same 10 context messages; pools of 2,037 DGG and 7,765 Hasan messages), seed 20261119, with every message coded on
  Nov 12 removed first. The 250 per side from Nov 12 suggested the hypothesis, so they are not part of this test.
- **Coder:** `claude-opus-5-5` at effort low only, with the Nov 12 prompt and schema unchanged (the owner chose one
  model for cost; on Nov 12 it agreed with Fable on 87% of stances). Cost limit set by the owner: $15.
- **"Endorsed antisemitism"** below = stance endorse with category antisemitism or holocaust_distortion, as in
  prediction 7. "JDA" = endorse with jda_antisemitic true.

| # | Prediction | Confidence |
|---|---|---|
| 10 | Endorsed antisemitism in the Hasan sample is 1.5-5%; in the DGG sample 0.5-3%. | medium |
| 11 | The Hasan share is higher than the DGG share. | 75% |
| 12 | The difference is clear: the 95% interval for Hasan minus DGG (Newcombe) excludes zero. | 50% |
| 13 | At least half of the Hasan endorsed items are JDA-antisemitic (control or dual-loyalty claims rather than only Holocaust inversion). | medium |
| 14 | Among items with antisemitic_content true, the joke_or_bait share is higher in DGG than in Hasan. | 80% |

Scored only on the new 1,000 per side, with Wilson intervals; results are added to the results file, misses included.
