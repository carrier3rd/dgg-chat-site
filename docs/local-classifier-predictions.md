# A trained local classifier (and a local screener): design and predictions

Written Nov 19, 2026, 9:20 PM ET, before any classifier is trained and before the local model sees any item of the
1,000-per-side sample. Follows `local-coder-agreement-results.md`, where prompting `qwen3:8b` failed twice. Never
edit; addenda go at the end. Results go in `local-classifier-results.md`.

## Design (frozen)

**Data.** All 3,285 items Claude Opus 5.5 has coded: the Nov 12 study (1,285) and the 1,000-per-side on-topic sample
(2,000). The answer key is Opus's code. Opus labels: 107 endorse, 340 antisemitic content. Chat text stays private
on the owner's machines; this repo gets aggregates only.

**Classes.** One three-way label from Opus's code: *not* (antisemitic_content false), *endorse* (content true and
stance endorse), *other* (content true, any other stance). Content = endorse or other.

**Model.** `microsoft/deberta-v3-base`, fine-tuned on the PC GPU. Input: the target message, a separator, then the
chat lines before it, newest first, cut at 320 tokens. Settings fixed in advance: learning rate 2e-5, 4 epochs,
batch 16, linear warmup 10%, weight decay 0.01, class weights 1/sqrt(class share), seed 7. No settings are tuned on
test folds.

**Evaluation.** 5-fold cross-validation grouped by stream unit (a day of DGG chat or one Hasan VOD), so no stream is
in both training and test, stratified by class as far as grouping allows (`StratifiedGroupKFold`, seed 7). Every
item gets one prediction from the fold where it was held out. Labels are the argmax.

**Bar (the same as for the prompted local model).** Against Opus, out of fold, on all 3,285 items: kappa(endorse) at
least 0.55 and content kappa at least 0.65. For reference, Opus vs Fable 5.2 on the Nov 12 study scored 0.639 and
0.776. On the Nov 12 subset it is also scored against Fable, as a check that it has not just learned Opus's quirks.

**Fallback: screener.** A screener only removes items so that Claude codes the rest; it passes if it keeps at least
95% of Opus's endorse items while sending at most 65% of items on to Claude.
- *Classifier screener:* flag when P(content) is at or above a threshold set inside each training fold (on a 15%
  group-held-out slice of it) as the lowest value that keeps 95% of that slice's endorse items.
- *Ollama screener:* `qwen3:8b` with the run 1 prompt unchanged, on the 2,000 items of the 1,000-per-side sample,
  which it has never seen. Flag when it codes antisemitic content or any stance other than not applicable. (On the
  Nov 12 items, read after run 1, this rule kept 55 of 56 endorse items and flagged 57%: that was post hoc, so this
  is the real test.)

If the classifier passes the bar it can code future samples in place of Claude, with a fresh Claude check sample
each time. If only a screener passes, it is used to cut what Claude codes. If neither passes, coding stays with Claude.

## Predictions

| # | Prediction | Confidence |
|---|---|---|
| 1 | Classifier kappa(endorse) vs Opus is 0.35-0.60. | medium |
| 2 | Classifier content kappa vs Opus is 0.55-0.78. | medium |
| 3 | The classifier passes the whole bar. | 25% |
| 4 | On the Nov 12 subset, its kappa(endorse) with Fable is lower than with Opus, by 0.02-0.15. | medium-low |
| 5 | The classifier screener keeps at least 90% of endorse items and flags at most 50% of items. | medium-low |
| 6 | The Ollama screener keeps 88-100% of endorse items on the new sample. | medium |
| 7 | The Ollama screener flags 40-70% of the new sample. | medium |
| 8 | The Ollama screener passes its bar (at least 95% kept, at most 65% flagged). | 45% |

## Scoring

Each prediction is a hit or a miss on these numbers. Rates get 95% Wilson intervals, kappas a bootstrap interval
over stream units (2,000 draws, seed 7). Misses are reported.
