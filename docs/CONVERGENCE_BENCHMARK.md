# MFLAB-CONVERGENCE-BENCH-0.1

## Purpose

`mflab benchmark-convergence` measures the current review-escalation behavior as a binary screening decision on labeled media. It reports two related decisions:

1. **Fusion review** — positive when `synthetic_evidence_fusion.convergence_level` is `moderate_convergence_for_expert_review` or `high_convergence_for_expert_review`.
2. **Protocol review** — positive when `deepfake_protocol.triage_assessment == needs_expert_review`.

The command does **not** tune thresholds. It measures the rules exactly as they exist in the analyzed commit.

## Metrics

For each decision it writes:

- confusion matrix (`TN`, `FP`, `FN`, `TP`);
- sensitivity / true-positive rate;
- specificity / true-negative rate;
- false-positive rate;
- false-negative rate;
- precision;
- accuracy;
- balanced accuracy;
- Wilson 95% intervals for sensitivity and specificity.

## Controlled pilot

Without arguments, the command uses the eight image fixtures in `dataset/demo`. Synthetic-positive ground truth is defined explicitly as:

- `label == synthetic`, or
- `method` beginning with `synthetic_`.

This makes `img_007_deepfake_face.jpg` and `img_008_ai_generated.png` positive controls; the other controlled image fixtures are non-synthetic controls.

The resulting rates are **pilot descriptive metrics only**. `dataset/demo` is small and engineered for regression coverage. It is not a population-representative corpus and does not establish forensic validity.

## External manifest

Use a CSV to benchmark a larger locked corpus:

```csv
case_id,path,expected_synthetic,source
real-001,/data/real/001.jpg,0,camera-control
ai-001,/data/ai/001.png,1,generator-A
```

Run:

```bash
mflab benchmark-convergence \
  --manifest benchmark/manifests/convergence_example.csv \
  --out validation/scientific/convergence_benchmark.json
```

`expected_synthetic` accepts `0/1`, `true/false`, `real/synthetic`, `non_synthetic`, `deepfake` and `ai`.

## Scientific interpretation

A useful external validation corpus should be locked before evaluation and should vary generator family, real-camera sources, image content, resolution, resizing, recompression, screenshotting and platform transformations. Report class prevalence and per-subgroup performance; do not use the same benchmark to tune the screening thresholds and then quote its metrics as an independent final test.

`needs_expert_review` remains a triage state. Neither a positive fusion decision nor a positive protocol decision is an evidentiary conclusion of synthetic generation.
