# Second Synthetic Classifier — AI-GenBench + frozen DINOv2

## Goal

Add a second, methodologically distinct machine opinion for real-vs-synthetic image screening without replacing the existing CIFAKE handcrafted/HGB classifier.

The target architecture is:

```text
image
  -> frozen DINOv2-S/14 backbone
  -> 384-D CLS embedding
  -> StandardScaler
  -> LogisticRegression
  -> disjoint Platt calibration
  -> score_synthetic + real/synthetic machine vote
```

The second classifier is intentionally different from the CIFAKE model, which uses the `synthetic_handcrafted_v2` feature bank and a calibrated HistGradientBoosting classifier. Agreement or disagreement between the models is information for triage; neither vote is an evidentiary conclusion.

## Why AI-GenBench

AI-GenBench is an ongoing benchmark designed around temporal generalization to future generators. Its official metadata currently describes 36 synthetic generators from 2017 through 2024. The published dataset statistics report, for the standard build:

- train: 144,000 real + 144,000 synthetic;
- validation: 36,000 real + 36,000 synthetic;
- each synthetic generator contributes 4,000 train and 1,000 validation images;
- train and validation have no overlapping images.

Upstream source:

- https://github.com/MI-BioLab/AI-GenBench
- `dataset_creation/resources/DATASET_STATS.md`
- `training_and_evaluation/ai_gen_bench_metadata/benchmark_generators.py`

The upstream benchmark uses chronologically ordered sliding windows of four generators. MFLab adopts that idea for its first OOD pilot rather than doing a random image-level split.

## Initial OOD holdout

The default immediate-future holdout is the latest chronological four-generator window in the current upstream metadata:

1. Stable Diffusion XL 1.0 — 2023-07-26
2. DALL-E 3 — 2023-09-20
3. FLUX 1 Dev — 2024-08-01
4. FLUX 1 Schnell — 2024-08-02

These generators are excluded from `fit` and appear only in `ood_test` during the pilot.

## Pilot sampling plan

The first run deliberately avoids processing all 360k images. AI-GenBench already balances synthetic generators, so the pilot uses nested per-generator sampling rather than naive random sampling.

Default maximum pilot:

- fit: 500 synthetic images per seen generator;
- fit real controls: equal total count, sampled round-robin across real origin datasets;
- calibration: 125 synthetic per seen generator + equal real controls;
- IID test: a different 125 synthetic per seen generator + equal real controls;
- OOD test: 500 synthetic per held-out generator + equal real controls.

With 32 seen generators and 4 held-out generators this yields:

- fit: 16,000 synthetic + 16,000 real = 32,000;
- calibration: 4,000 + 4,000 = 8,000;
- IID test: 4,000 + 4,000 = 8,000;
- OOD test: 2,000 + 2,000 = 4,000;
- total embeddings in the initial pilot: 52,000.

The fit rows are nested using `sample_rank`, enabling learning-curve stages such as 125, 250 and 500 images per seen generator without recomputing embeddings.

Expected fit sizes:

| Stage | Synthetic fit | Real fit | Total fit |
|---:|---:|---:|---:|
| 125/generator | 4,000 | 4,000 | 8,000 |
| 250/generator | 8,000 | 8,000 | 16,000 |
| 500/generator | 16,000 | 16,000 | 32,000 |

If the OOD learning curve is still improving materially, the same cache/protocol can be expanded to 1,000, 2,000 and eventually all 4,000 train images per seen generator.

## Real-image balancing

A classifier can accidentally learn dataset-source cues rather than synthetic-image cues. MFLab therefore does not simply draw real controls in proportion to source-dataset size. Real rows are independently shuffled per `origin_dataset` and selected round-robin without replacement. Small origins are exhausted and remaining origins fill the quota.

This is a pilot anti-confounding measure, not a claim that all real-image domains are fully represented.

## Leakage controls

The manifest builder enforces:

- no duplicate sample IDs;
- no synthetic generator overlap between `fit` and `ood_test`;
- class balance inside each role;
- fit from AI-GenBench `train` only;
- calibration/IID/OOD from disjoint rows of `validation`;
- held-out OOD generators never enter model fitting or calibration.

## Embedding cache

DINOv2 remains frozen. The expensive operation is therefore performed once:

```text
image -> DINOv2 CLS embedding -> .npz cache
```

The default backbone is `facebook/dinov2-small`, whose CLS representation is 384-dimensional. At 52,000 examples, raw float32 embeddings are approximately 80 MB before compressed metadata overhead.

Once cached, classifier experiments are cheap and can compare linear/logistic heads or other shallow models without reopening every image or rerunning the backbone.

## Calibration

The decision boundary is fit only on `fit`. A separate `calibration` role is transformed into one-dimensional decision scores, and a logistic Platt calibrator is fitted to those scores. `iid_test` and `ood_test` remain untouched until evaluation.

The default threshold is 0.5, but threshold optimization is not performed on the test sets.

## Metrics

Each learning-curve stage reports independently for IID and generator-OOD test sets:

- accuracy;
- balanced accuracy;
- precision;
- sensitivity;
- specificity;
- FPR;
- FNR;
- F1;
- ROC-AUC;
- PR-AUC;
- Brier score;
- TN/FP/FN/TP;
- Wilson 95% intervals for sensitivity and specificity.

The OOD result is the primary generalization result. IID performance is secondary diagnostic information.

## Scientific status

The first exported head is marked:

```text
scientific_status = pilot_internal_aigenbench
validated = false
```

This is intentional. Internal AI-GenBench IID/OOD performance is not enough to call the model universally validated. Before production promotion, the model should be challenged on datasets not used to build the classifier, preferably including Synthbuster and Chameleon, plus a held-out MFLab regression set containing modern synthetic images.

The known OpenAI-generated test image used during MFLab development must remain outside training so it can serve as an OOD regression case.

## Commands

Install optional dependencies:

```bash
pip install -e '.[second]'
```

Build the pilot manifest from a locally constructed AI-GenBench DatasetDict:

```bash
python scripts/second_synthetic_classifier.py build-manifest \
  --dataset-path /data/ai_gen_bench_v1.0.0 \
  --out work/second_classifier/manifest.csv
```

Extract embeddings:

```bash
python scripts/second_synthetic_classifier.py extract-embeddings \
  --dataset-path /data/ai_gen_bench_v1.0.0 \
  --manifest work/second_classifier/manifest.csv \
  --out work/second_classifier/dinov2_embeddings.npz \
  --device auto
```

Train the nested learning curve and final calibrated head:

```bash
python scripts/second_synthetic_classifier.py train-head \
  --embeddings work/second_classifier/dinov2_embeddings.npz \
  --model-out work/second_classifier/mflab_aigenbench_dinov2s14_logreg_calibrated_v1.joblib \
  --result-out work/second_classifier/result.json \
  --learning-curve 125,250,500
```

## Not yet integrated into production

This branch creates the research/training pipeline only. It does **not** yet:

- bundle the DINOv2 backbone into the normal MFLab runtime;
- add the second vote to `full` analysis;
- fuse Classifier 1 and Classifier 2 scores;
- alter `evidentiary_conclusion`;
- deploy a new Railway version.

Those steps should happen only after the pilot metrics and external validation are reviewed.
