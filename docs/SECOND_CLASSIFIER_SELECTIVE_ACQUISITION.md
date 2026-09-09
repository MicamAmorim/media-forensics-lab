# Selective acquisition for the second synthetic classifier

## Objective

The first Classifier 2 pilot should not require a full local copy of AI-GenBench merely to extract 52,000 frozen embeddings. The selective acquisition path builds an auditable plan first and downloads only the selected image bytes.

The official AI-GenBench fake part is published on Hugging Face as Parquet. Hugging Face Dataset Viewer exposes row/filter endpoints that can query Parquet-backed datasets without downloading complete Parquet shards. MFLab uses those endpoints to enumerate one generator at a time, caches the JSON pages, applies its deterministic per-generator selection, and then materializes only the selected image URLs.

The real controls are selected from the official AI-GenBench `train_real_file_ids.txt` and `validation_real_file_ids.txt` lists. The initial selective resolver supports the two reproducible public acquisition paths used heavily by the benchmark:

- COCO 2017: direct `images.cocodataset.org` image URLs;
- LAION-400M ELSA-D3 subset: URLs resolved from the compact official AI-GenBench LAION filelist ZIPs.

RAISE is intentionally not silently substituted because its acquisition requires the source package/CSV and associated access terms. If a later protocol requires RAISE, it must be added explicitly and documented rather than replaced by another source.

## Byte-preserving policy

Downloaded images are not re-encoded. The materializer:

1. downloads the source bytes;
2. verifies that PIL can decode the image;
3. infers only the file extension from the decoded format;
4. writes the original bytes unchanged;
5. records SHA-256 in the materialized manifest.

This avoids introducing JPEG/resampling artifacts during dataset preparation.

## Resumability

Dataset Viewer pages are cached under the requested cache directory. Already materialized images are re-used after decode verification and their SHA-256 is recomputed. An interrupted acquisition can therefore be resumed without restarting the full scan or redownloading completed files.

## Completeness gate

Embedding extraction is intentionally strict. Before DINOv2 runs, every row in the materialized manifest must:

- point to an existing local file;
- carry a 64-character SHA-256 digest;
- preserve class balance inside each role.

A dead LAION URL, failed COCO download or unresolved source therefore stops the scientific run. The pipeline will not silently shrink the sample and continue training on a different distribution.

## Workflow

Install research dependencies:

```bash
pip install -e '.[second]'
```

### 1. Build the remote plan

```bash
python scripts/second_classifier_acquire.py build-plan \
  --cache-dir work/second_classifier/cache \
  --out work/second_classifier/acquisition-plan.csv
```

Default target:

- fit: 500 synthetic per 32 seen generators + 16,000 real;
- calibration: 125 synthetic per seen generator + 4,000 real;
- IID test: separate 125 synthetic per seen generator + 4,000 real;
- OOD test: 500 synthetic per four held-out generators + 2,000 real;
- total: 52,000 images.

The four default OOD generators remain SDXL 1.0, DALL-E 3, FLUX 1 Dev and FLUX 1 Schnell.

### 2. Smoke-test acquisition before the full sample

```bash
python scripts/second_classifier_acquire.py materialize \
  --plan work/second_classifier/acquisition-plan.csv \
  --output-dir work/second_classifier/images \
  --out work/second_classifier/materialized-smoke.csv \
  --max-samples 100
```

Inspect the summary JSON and failures before starting all 52,000 downloads.

### 3. Materialize the full selected sample

```bash
python scripts/second_classifier_acquire.py materialize \
  --plan work/second_classifier/acquisition-plan.csv \
  --output-dir work/second_classifier/images \
  --out work/second_classifier/materialized.csv
```

### 4. Extract frozen DINOv2 embeddings

```bash
python scripts/second_classifier_acquire.py extract-embeddings \
  --manifest work/second_classifier/materialized.csv \
  --out work/second_classifier/dinov2_embeddings.npz \
  --device auto \
  --batch-size 32
```

This command first applies the completeness gate described above.

### 5. Train the calibrated head and learning curve

The output NPZ is compatible with the existing Classifier 2 training command:

```bash
python scripts/second_synthetic_classifier.py train-head \
  --embeddings work/second_classifier/dinov2_embeddings.npz \
  --model-out work/second_classifier/mflab_aigenbench_dinov2s14_logreg_calibrated_v1.joblib \
  --result-out work/second_classifier/result.json \
  --learning-curve 125,250,500
```

## Scientific constraints

Selective acquisition changes storage/transfer cost, not the scientific split. The following remain invariant:

- synthetic sampling is per generator;
- fit and calibration are disjoint;
- IID test is untouched by fitting/calibration;
- OOD generators never enter fit or calibration;
- real controls are selected from the official AI-GenBench file-ID lists;
- the test threshold is not optimized on IID/OOD results;
- the OpenAI-generated MFLab regression image remains outside training.

The resulting model remains `pilot_internal_aigenbench`, `validated=false`, and `screening_only` until external validation is completed.
