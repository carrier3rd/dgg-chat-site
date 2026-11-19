# Can a local model replace the paid coders? Results

Scores `local-coder-agreement-predictions.md` (committed before any study item was sent to the local model). Run 1
finished Nov 19, 2026 at 16:11 EST. Aggregates only: per-item codes hold chat text and stay private.

## Run 1: `qwen3:8b`, the Nov 12 prompt unchanged

All 1,285 items coded, all outputs schema-valid, median 4.9 s per item.

| Measure | Local vs Opus 5.5 | Local vs Fable 5.2 | Opus vs Fable (benchmark) | Bar |
|---|---|---|---|---|
| Stance agreement | 0.475 | 0.490 | 0.872 | 0.80 |
| kappa(endorse) | 0.121 | 0.101 | 0.639 | 0.55 |
| Stance kappa | 0.147 | 0.162 | 0.597 | — |
| Content kappa | 0.278 | 0.310 | 0.776 | 0.65 |
| Items coded endorse | 364 | 364 | 45 / 38 | — |

Schema-valid 100%; non-empty quotes verbatim 98.5%. **It fails the bar on every agreement measure** and is not used
for the larger sample.

### Predictions

| # | Prediction | Result |
|---|---|---|
| 1 | At least 98% schema-valid | **Hit** (100%) |
| 2 | Stance agreement 72-84% with each | **Miss**: 47.5% and 49.0%, far below the range |
| 3 | kappa(endorse) 0.30-0.55, below the bar | **Miss**: below the bar as predicted, but 0.12 and 0.10, under the range |
| 4 | Content kappa 0.55-0.75 | **Miss**: 0.28 and 0.31 |
| 5 | More endorse codes than either Claude coder | **Hit** (364 vs 45 and 38) |
| 6 | Agrees more with Opus than with Fable on stance | **Miss** (0.475 vs 0.490) |
| 7 | At least 90% of quotes verbatim | **Hit** (98.5%) |
| 8 | Fails the bar overall | **Hit** |

4 of 8 hit. The misses all go the same way: the predictions expected a weaker coder, not one this far off.

### What went wrong (diagnosis, Nov 19)

On the 1,121 items where the two Claude coders agree on stance, 254 of the local model's endorse codes fall on
items both coded otherwise, and 191 of those both coded as not antisemitic at all. The main failure is detecting
content, not reading stance. Reading a random sample of the disagreements, and questioning the model with its
reasoning switched on, showed four patterns:

1. **The keyword list read as proof.** The prompt's reference list of dog whistles (e.g. "Zionist", "Israel lobby",
   "George Soros", "109") was taken as a dictionary: a match was coded antisemitic whatever the sentence said. In 52
   of these false positives its reason names ZOG although the message does not mention it.
2. **Invented meanings.** Unknown abbreviations and emote names were given made-up antisemitic meanings, which then
   counted as evidence.
3. **Talking about antisemitism read as antisemitism.** Messages that condemn or describe antisemitism were coded as
   endorsing it (13 of the 15 items both Claude coders called condemn).
4. **Tone markers ignored.** Laughing and meme emotes did not move it from endorse to joke.

It was also internally inconsistent: 154 joke codes with content false, and 94 IHRA/JDA flags without endorse.

## Run 2: `qwen3:8b`, prompt v2 (addendum 2)

Finished Nov 19, 2026 at 6:56 PM EST. All 1,285 items coded, all schema-valid, all quotes verbatim, median 5.0 s.

| Measure | v2 vs Opus 5.5 | v2 vs Fable 5.2 | Held out, vs Opus / Fable (1,218 unread items) | Bar |
|---|---|---|---|---|
| Stance agreement | 0.811 | 0.812 | 0.818 / 0.819 | 0.80 |
| kappa(endorse) | 0.126 | 0.142 | 0.130 / 0.148 | 0.55 |
| Stance kappa | 0.284 | 0.264 | 0.257 / 0.233 | — |
| Content kappa | 0.332 | 0.333 | 0.316 / 0.307 | 0.65 |
| Items coded endorse | 55 | 55 | 47 | — |

**It fails the bar** on kappa(endorse) and content kappa, on all items and on the held-out items. Stance agreement
passes, but mostly through the 956 items that both Claude coders and v2 call not applicable.

### Predictions 9-16

| # | Prediction | Result |
|---|---|---|
| 9 | At least 98% schema-valid | **Hit** (100%) |
| 10 | 30-150 endorse codes | **Hit** (55) |
| 11 | Content kappa at least 0.50 with each | **Miss** (0.33, 0.33) |
| 12 | Content kappa at least 0.65 with each | **Miss** |
| 13 | Stance agreement at least 80% with each | **Hit** (81.1%, 81.2%) |
| 14 | kappa(endorse) at least 0.55 with each | **Miss** (0.13, 0.14) |
| 15 | Held-out measures within 0.05 of all-items values | **Hit** (largest gap 0.031) |
| 16 | Passes the whole bar | **Miss** (given 20%) |

### What changed

The prompt moved the error rather than removing it. Of the 139 items both Claude coders mark antisemitic, v2 marks
54 and misses 85; on 81 of the misses its first step said the message does not refer to Jews. It still marks 64
items neither Claude coder does, mostly as control claims. On the 15 items both call condemn, it never answered that
the author calls the content wrong. Tone improved: it called 58 of the 78 agreed joke items jokes. Held-out and
all-items numbers match, so the result is not an artefact of the items read while writing the prompt.

**Conclusion:** at 8B and 4-bit, prompting alone does not bring the local model to the bar. The larger on-topic sample
stays with the Claude coders unless a different local setup (a larger model, or one trained on coded items) is
tested under new predictions.
