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
