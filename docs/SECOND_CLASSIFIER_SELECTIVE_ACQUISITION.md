# Selective acquisition for the second synthetic classifier

## Objective

The first Classifier 2 pilot should not require a full local copy of AI-GenBench merely to extract 52,000 frozen embeddings. MFLab first builds an auditable plan, then materializes only the selected images.

The synthetic side is read from the published AI-GenBench fake part on Hugging Face. Dataset Viewer `/filter` and `/search` proved unreliable for this large image dataset during live CI (504/500 responses), so the current resolver uses deterministic `/rows` page scanning and stops as soon as each requested generator quota is satisfied. Full Parquet shards are not required for the pilot.

The real controls still originate from the official AI-GenBench `train_real_file_ids.txt` and `validation_real_file_ids.txt` lists, but acquisition is stabilized by source:

- COCO 2017: official `train2017.zip` / `val2017.zip` archives are downloaded once and only selected members are read from each ZIP;
- LAION-400M ELSA-D3 subset: original URLs are attempted first; dead URLs are replaced from a deterministic reserve pool drawn from the same official split/source and every substitution is logged;
- RAISE is not silently substituted because its source/access conditions differ.

Because the resulting real corpus is reconstructed from official IDs and then stabilized by MFLab, the pilot corpus is named **MFLab AI-GenBench-derived v1**, not simply “AI-GenBench”.

## Why COCO uses archives

Thousands of individual `images.cocodataset.org/...jpg` requests were not reliable in the GitHub Actions smoke. The stable path instead downloads each required official ZIP once. The materializer opens the archive without re-encoding images, reads only the selected members, verifies decodability, writes the original member bytes, and records SHA-256.

The archive is cacheable and resumable. A partial `.part` file is resumed with HTTP Range when supported. After the selected corpus has been frozen, the large source archive may be deleted if local storage is needed; the frozen selected images remain sufficient for subsequent embedding/training runs.

## LAION dead-URL policy

Historical LAION URLs can disappear. Silent sample shrinkage is forbidden.

For each split, MFLab builds a deterministic reserve ordering from official LAION IDs that were not selected in the original plan. If a planned URL fails:

1. the original failure is recorded with host, HTTP status when available, exception type, attempt count, elapsed time and reason;
2. reserve candidates are attempted in deterministic order;
3. the first decodable replacement from the same LAION split/source fills that scientific slot;
4. the final replacement ID/URL/SHA-256 and the original failed ID/URL are written to the replacement log;
5. if no replacement succeeds within the configured bound, the sample remains failed and the completeness gate blocks training.

No replacement is drawn from the test result itself, and reserve IDs are not reused.

## Byte-preserving policy

Images are not re-encoded during acquisition. For direct synthetic/LAION downloads and COCO ZIP members, the materializer:

1. obtains the source bytes;
2. verifies that PIL can decode the image;
3. infers only the filename extension from the decoded format;
4. writes the original bytes unchanged;
5. records SHA-256.

This avoids adding JPEG/resampling artifacts during dataset preparation.

## HTTP diagnostics

The stable downloader records, when available:

- original URL;
- host;
- final URL after redirects;
- HTTP status;
- exception type;
- failure reason;
- number of attempts;
- elapsed time.

Diagnostics are emitted separately from the scientific manifest so acquisition failures remain inspectable without changing the training schema.

## Completeness gate

Before DINOv2 runs, every materialized row must:

- point to an existing local file;
- carry a valid 64-character SHA-256;
- preserve class balance inside every role.

Dead URLs or missing archive members therefore stop the scientific run rather than silently changing the sample.

## Frozen corpus

Once acquisition succeeds, `freeze-corpus` recomputes every SHA-256 and writes:

- a canonical frozen manifest;
- a SHA-256 of that frozen manifest;
- role/class and origin counts;
- optional replacement-log hash;
- an immutable corpus identifier such as `mflab-aigenbench-derived-v1-<digest>`.

Training and future reproductions should use this frozen corpus, not re-resolve internet URLs each time.

## Workflow

Install research dependencies:

```bash
pip install -e '.[second]'
```

### 1. Build the deterministic plan

```bash
python scripts/second_classifier_acquire.py build-plan \
  --cache-dir work/second_classifier/cache \
  --out work/second_classifier/acquisition-plan.csv
```

Default target:

- fit: 500 synthetic per 32 seen generators + 16,000 real;
- calibration: 125 synthetic per seen generator + 4,000 real;
- IID test: a different 125 synthetic per seen generator + 4,000 real;
- OOD test: 500 synthetic per four held-out generators + 2,000 real;
- total: 52,000 images.

The default OOD generators remain SDXL 1.0, DALL-E 3, FLUX 1 Dev and FLUX 1 Schnell.

### 2. Materialize with the stable source policy

```bash
python scripts/second_classifier_acquire.py materialize-stable \
  --plan work/second_classifier/acquisition-plan.csv \
  --cache-dir work/second_classifier/cache \
  --archive-cache work/second_classifier/source-archives \
  --output-dir work/second_classifier/images \
  --out work/second_classifier/materialized.csv \
  --diagnostics-out work/second_classifier/acquisition-diagnostics.json \
  --replacement-log-out work/second_classifier/replacements.json
```

The legacy `materialize` command remains available for small diagnostics, but the scientific pilot should use `materialize-stable`.

### 3. Freeze the complete corpus

```bash
python scripts/second_classifier_acquire.py freeze-corpus \
  --manifest work/second_classifier/materialized.csv \
  --frozen-manifest work/second_classifier/frozen-manifest.csv \
  --lock work/second_classifier/corpus.lock.json \
  --replacement-log work/second_classifier/replacements.json
```

If this succeeds, all source bytes and hashes have been rechecked and the corpus receives a stable ID.

### 4. Extract frozen DINOv2 embeddings

```bash
python scripts/second_classifier_acquire.py extract-embeddings \
  --manifest work/second_classifier/materialized.csv \
  --out work/second_classifier/dinov2_embeddings.npz \
  --device auto \
  --batch-size 32
```

This command independently applies the completeness gate again.

### 5. Train the calibrated head and learning curve

```bash
python scripts/second_synthetic_classifier.py train-head \
  --embeddings work/second_classifier/dinov2_embeddings.npz \
  --model-out work/second_classifier/mflab_aigenbench_dinov2s14_logreg_calibrated_v1.joblib \
  --result-out work/second_classifier/result.json \
  --learning-curve 125,250,500
```

## Scientific constraints

Stable acquisition changes transfer/storage mechanics, not the intended experiment:

- synthetic sampling remains per generator;
- fit and calibration remain disjoint;
- IID test remains untouched by fitting/calibration;
- OOD generators never enter fit or calibration;
- real controls start from official AI-GenBench file-ID lists;
- LAION substitutions stay inside the same source and split and are fully logged;
- COCO bytes come from official source archives;
- the test threshold is not optimized on IID/OOD results;
- the known OpenAI-generated MFLab regression image remains outside training.

The resulting model remains `pilot_internal_aigenbench`, `validated=false`, and `screening_only` until external validation is completed.
