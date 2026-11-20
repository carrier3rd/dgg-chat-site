# Can a local model replace the paid coders? Agreement on the Nov 12 antisemitism coding items: predictions

Written Nov 19, 2026, before any study item was sent to the local model (only one made-up item was run, to check
speed and memory). Never edit; addenda go at the end. Results go in `local-coder-agreement-results.md`.

## Why

The Nov 12 study (`dgg-hasan-antisemitism-coding-results.md`) ends by saying a larger on-topic sample is needed
before claiming a DGG/Hasan difference. Coding it with the paid models was estimated at $60-80 and put on hold. A
model running on the project's own GPU costs nothing per item. This checks whether it codes well enough to use.

## Setup (frozen)

- Model: `qwen3:8b` (4-bit, Ollama 0.40.16) on an RTX 4050 laptop GPU, thinking off, temperature 0, seed 7,
  context 4,608 tokens, output constrained to the study's JSON schema.
- Task: identical to the Nov 12 batches: the same system prompt, the same per-item prompt (target message, 10
  context messages with aliases, keyword hits) and the same schema, for all 1,285 items (785 keyword candidates, 500
  on-topic non-candidates; both sides shuffled).
- Compared with each Claude coder separately (`claude-opus-5-5` effort low, `claude-fable-5-2` effort high).
- Measures, all on items both coders returned: stance agreement (share with the same of six stance values);
  kappa(endorse) (Cohen's kappa on stance = endorse vs not); stance kappa (six values); content kappa
  (antisemitic_content true/false). Plus: share of schema-valid outputs, share of non-empty quotes found verbatim in
  the target.
- Benchmark: the two Claude coders agreed with each other at 87.2% on stance, kappa(endorse) 0.64, stance kappa 0.60,
  content kappa 0.78 (Nov 12 results, prediction 8). The local model's agreement with each is set against that.

## Bar for using it (frozen)

The local model may code the larger on-topic sample only if, against **both** Claude coders: stance agreement at
least 80%, kappa(endorse) at least 0.55, content kappa at least 0.65; and at least 98% of outputs are schema-valid
and at least 95% of non-empty quotes are verbatim. Failing any one means it is not used for that study.

## Predictions

| # | Prediction | Confidence |
|---|---|---|
| 1 | At least 98% of outputs are schema-valid. | high |
| 2 | Stance agreement with each Claude coder is 72-84%. | medium |
| 3 | kappa(endorse) with each Claude coder is 0.30-0.55, below the bar. | medium |
| 4 | Content kappa with each Claude coder is 0.55-0.75. | medium |
| 5 | The local model codes more items as endorse than either Claude coder (it takes keyword hits at face value more often). | medium-low |
| 6 | It agrees more with Opus 5.5 (effort low) than with Fable 5.2 (effort high) on stance. | low |
| 7 | At least 90% of its non-empty quotes are verbatim. | medium |
| 8 | Overall it fails the bar. | 60% |

## Scoring

Each prediction is a hit or a miss on the numbers above, reported in the results file with both comparisons, misses
included. Per-item codes stay private (they hold chat text); only aggregates are published.

## Addendum, Nov 19 2026, before any results were read

Runtime changed so the whole model runs on the GPU: all layers on the GPU (`num_gpu` 99), flash attention on, and
the attention cache stored at 8 bits (`OLLAMA_KV_CACHE_TYPE=q8_0`). Model, prompts, schema, temperature, seed and
context are unchanged. These settings can shift outputs slightly, so the first run (about 100 items, under the old
settings) was stopped and set aside unread and unscored, and the run restarted from the first item. Speed on the
made-up check item went from about 11 to 4.8 seconds. Predictions and the bar are unchanged.

Correction, Nov 19 2026 (same day, still before any results were read): the set-aside first run held 15 items,
not about 100. They were counted, not read.

## Addendum 2, Nov 19 2026: run 2 with a new prompt (v2), written before run 2 started

Run 1 failed the bar (results in `local-coder-agreement-results.md`). Run 2 tests a prompt written for the local
model. Model, runtime settings, items, per-item prompt and the comparison with the Claude coders are unchanged.
**The bar is unchanged**, and the Claude codes are still the answer key.

What changed:
- **System prompt v2.** Same coding rules as Nov 12, rewritten as a step-by-step procedure aimed at the four run-1
  failures: the keyword list is no longer given as a dictionary (only the matched keyword ids are shown); the model
  must copy the exact words that carry a trope before naming one; condemning or describing antisemitism is spelled
  out as not antisemitic content; emotes and unknown slang may not be read as codes. It has 12 worked examples, all
  made up for the prompt; none is a study item.
- **Step fields, then fixed rules.** The model answers seven step fields (refers to Jews; plain meaning; the exact
  trope words; which trope; does the author call it wrong; is the author repeating someone; tone) plus irony kind,
  pattern ids, quote and reason. The study labels (content, stance, target, categories, IHRA, JDA) are then set from
  those answers by fixed rules in code, following the Nov 12 conventions. A trope only counts if its quoted words
  appear verbatim in the target.
- **What the prompt writer saw.** The prompt was written after reading 67 study items where run 1 went wrong (ids
  recorded privately before run 2) and the model's answers to follow-up questions on 10 of them. The scores are
  therefore reported twice: on all 1,285 items, and on the 1,218 items the writer never read. The held-out figure
  is the one that counts for prompt quality; the bar is applied to both, and run 2 passes only if both pass.
- Smoke check before this addendum: 8 made-up messages, not study items; 7 coded as intended.

| # | Prediction for run 2 | Confidence |
|---|---|---|
| 9 | At least 98% of outputs schema-valid. | high |
| 10 | Fewer endorse codes than run 1: between 30 and 150. | medium |
| 11 | Content kappa with each Claude coder at least 0.50. | medium |
| 12 | Content kappa with each Claude coder at least 0.65 (the bar). | 35% |
| 13 | Stance agreement with each Claude coder at least 80% (the bar). | 45% |
| 14 | kappa(endorse) with each Claude coder at least 0.55 (the bar). | 25% |
| 15 | On the 1,218 held-out items, every agreement measure is within 0.05 of its all-items value. | medium |
| 16 | Run 2 passes the whole bar. | 20% |

## Addendum 3, Nov 19 2026, 11:15 PM ET: larger local models (runs 3 and 4), written before either started

Runs 1 and 2 put the 8B model well short of the bar. Runs 3 and 4 test whether a larger model, still free and
runnable at home or on a cheap rented GPU, closes the gap, with the run 1 setup otherwise unchanged.

- **Models.** Run 3: `qwen3:14b`. Run 4: `qwen3:32b`. Both 4-bit, from the Ollama library, on a rented RTX 4090
  (24 GB, Runpod Secure Cloud), Ollama 0.40.16, all layers on the GPU, flash attention on, 8-bit attention cache,
  thinking off, temperature 0, seed 7, context 4,608 tokens, output constrained to the schema.
- **Task.** The run 1 task exactly: the Nov 12 system prompt (the one the Claude coders had, not the v2 prompt), the
  same per-item prompts and schema, all 1,285 items.
- **Comparison and bar.** Unchanged: each Claude coder separately, the same measures, the same bar (against both:
  stance agreement at least 80%, kappa(endorse) at least 0.55, content kappa at least 0.65; at least 98%
  schema-valid; at least 95% of non-empty quotes verbatim). Scores are also given on the 1,218 items never read
  while writing prompt v2, for comparability with run 2.
- **Order.** Run 3 first, then run 4. If run 4 cannot load fully on the GPU, it is not run and that is reported.

| # | Prediction | Confidence |
|---|---|---|
| 17 | Runs 3 and 4 each have at least 98% schema-valid outputs. | high |
| 18 | Run 3 kappa(endorse) with each Claude coder is 0.15-0.40. | medium |
| 19 | Run 4 kappa(endorse) with each Claude coder is 0.25-0.55. | medium |
| 20 | kappa(endorse) rises with size against both coders: run 4 > run 3 > run 1 (0.121 Opus, 0.101 Fable). | medium |
| 21 | Run 4 content kappa with each Claude coder is 0.40-0.70. | medium |
| 22 | Both runs code more items as endorse than either Claude coder (45 Opus, 38 Fable). | medium |
| 23 | Run 3 passes the whole bar. | 5% |
| 24 | Run 4 passes the whole bar. | 15% |
