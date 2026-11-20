# A trained local classifier (and a local screener): results

Scores `local-classifier-predictions.md` (design and predictions committed before training, c786c73; addendum on the
rented GPU and gradient checkpointing, 5a609c9). Finished Nov 20, 2026, 12:00 AM ET. Aggregates only: per-item
codes hold chat text and stay private.

**Score: 1 of 8 hit.** Neither the classifier nor either screener passes. Coding stays with the Claude coders.

## The classifier (`deberta-v3-base`, 5-fold cross-validation grouped by stream)

All 3,285 items got an out-of-fold prediction (32 stream units, 5 folds).

| Measure (vs Opus 5.5) | Result | 95% interval (bootstrap over stream units) | Bar |
|---|---|---|---|
| kappa(endorse) | **0.000** | 0.000-0.000 | 0.55 |
| Content kappa | **0.363** | 0.232-0.455 | 0.65 |
| Content kappa, DGG items / Hasan items | 0.382 / -0.001 | | |
| Content kappa vs Fable 5.2 (Nov 12 subset, 1,285 items) | 0.519 | | |

It never predicted endorse. Of Opus's 107 endorse items it put 84 in *not* and 23 in *other*; overall it labelled
239 items as antisemitic content against Opus's 336. With 107 endorse examples in 3,285 and the pre-set class
weights, the model settled on the two common classes. It learned some content signal on DGG chat and none on Hasan
chat.

## The screeners

| Screener | Endorse items kept | Items sent on to Claude | Bar (keep at least 95%, send at most 65%) |
|---|---|---|---|
| Classifier, P(content) at the in-fold threshold (all 3,285 items) | 86/107 (80.4%, 71.9-86.8%) | 2,693/3,285 (82.0%) | fails both |
| Ollama `qwen3:8b`, run 1 prompt (2,000 new items) | 54/62 (87.1%, 76.6-93.3%) | 1,151/2,000 (57.6%, 55.4-59.7%) | fails on items kept |

The Ollama screener coded all 2,000 items with no failures (median 1.4 s per item on the rented GPU). It also kept
164 of Opus's 176 antisemitic-content items (93%). On the Nov 12 items, read after run 1, the same rule had kept 55
of 56 endorse items; on fresh items it lost 8 of 62, so the post hoc figure was optimistic.

## Predictions

| # | Prediction | Result |
|---|---|---|
| 1 | Classifier kappa(endorse) vs Opus 0.35-0.60 | **Miss** (0.000) |
| 2 | Classifier content kappa vs Opus 0.55-0.78 | **Miss** (0.363) |
| 3 | Classifier passes the whole bar (25%) | **Miss** |
| 4 | On the Nov 12 subset, kappa(endorse) with Fable 0.02-0.15 lower than with Opus | **Miss** (both 0.000) |
| 5 | Classifier screener keeps at least 90% of endorse items and flags at most 50% | **Miss** (80.4%, 82.0%) |
| 6 | Ollama screener keeps 88-100% of endorse items | **Miss** (87.1%, just under) |
| 7 | Ollama screener flags 40-70% of items | **Hit** (57.6%) |
| 8 | Ollama screener passes its bar (45%) | **Miss** |

The misses all go the same way: both local approaches did worse than predicted, and the classifier much worse.

## What this means

- A small classifier trained on about 3,300 Claude-coded messages cannot find sincere antisemitism here: the
  positives are too rare and too varied for it.
- As a cost-cutter in front of Claude, the 8B model would drop about one sincere item in eight, too many for a
  measure of how common those items are. Claude codes everything, as before (about $6.50 per 2,000 items).
- Larger local models (`qwen3:14b`, `qwen3:32b`) are tested separately under addendum 3 of
  `local-coder-agreement-predictions.md`.
