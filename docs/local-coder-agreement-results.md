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

## Run 2 (prompt v2)

See the addendum at the end of the predictions file, committed before run 2 started. Results to follow below.
