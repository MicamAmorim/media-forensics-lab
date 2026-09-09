# Changelog

## 0.9.0 - 2026-09-09

### Added
- Bundled calibrated classifier `mflab_cifake_hgb_calibrated_v1` using the `synthetic_handcrafted_v2` feature bank.
- Reproducible CIFAKE training/export workflow with full feature extraction, model export, JSON/Markdown validation report and validation plots.
- Explicit `machine_assessment` object in `MFLAB-DF-0.7`, separating the computational `real`/`synthetic` vote from the forensic evidentiary conclusion.
- Interactive-report display of the automatic class label, synthetic score, model name and validation-scope status.
- Package-data support for the bundled `.joblib` model and its validation metadata.
- Fresh-holdout protocol that reconstructs the v0.8 development subset and reserves a disjoint holdout from its complement before the v0.9 model is evaluated.

### Changed
- Project version bumped to `0.9.0`.
- Synthetic-media protocol upgraded to `MFLAB-DF-0.7`.
- `synthetic_ml` now loads the bundled model by default unless `MFLAB_SYNTHETIC_MODEL` overrides it.
- A model's bundle-level validation is distinguished from `validated_for_input`; arbitrary evidence is not silently assumed to belong to the validation domain.
- scikit-learn is constrained to the Python-3.10-compatible model line `>=1.7.2,<1.8`.

### Scientific / forensic policy
- The bundled model is validated only in the declared CIFAKE domain: CIFAR-10 real versus Stable Diffusion v1.4 synthetic at 32×32 pixels.
- The official CIFAKE test set is retained as a secondary result because it was already inspected during v0.8 development; the primary v0.9 estimate uses a fresh disjoint holdout from the CIFAKE training pool.
- For arbitrary case images, the automatic label remains screening unless the examiner explicitly confirms domain applicability using `MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED=1`.
- `machine_assessment.label` is never promoted automatically to `evidentiary_conclusion`; the latter remains `inconclusive` absent documented expert convergence.

## 0.8.0 - 2026-09-08

### Added
- Clean-room AutoGAN-compatible spectral preprocessing for GAN upsampling artifact analysis.
- Per-channel FFT log-magnitude normalization using P5/P95 and `full`, `low`, `mid`, `high` frequency partitions compatible with the WIFS 2019 method.
- Descriptive AutoGAN feature family: band energy fractions, profile autocorrelation peaks, lag descriptors, quadrant-replication correlation and per-channel spectral statistics.
- Optional ResNet34 AutoGAN checkpoint adapter using `MFLAB_AUTOGAN_CHECKPOINT`, with lazy Torch/Torchvision loading and SHA-256 checkpoint provenance.
- Optional checkpoint metadata via sidecar JSON / `MFLAB_AUTOGAN_METADATA` for explicit calibration and validation state.
- AutoGAN visual artifacts (`autogan_fft_full/low/mid/high` and `autogan_spectral_profile`) integrated into the existing gallery and report appendix without redesigning the site.
- Scientific benchmark support for AutoGAN-compatible features and optional fixed-checkpoint evaluation on the untouched final test split.
- Tests covering spectral geometry, band partitioning, feature integration, optional checkpoint behavior, fusion policy and visual-artifact generation.
- Documentation `docs/AUTOGAN_INTEGRATION.md` and WIFS 2019 bibliography entry.

### Changed
- Project version bumped to `0.8.0`.
- Report schema bumped to `0.7`.
- `synthetic_handcrafted_v2` now includes AutoGAN-compatible spectral features.
- Synthetic-media protocol upgraded to `MFLAB-DF-0.6`.
- Scientific validation protocol upgraded to `MFLAB-SCI-SYNTH-0.3`.
- `mflab integrations` now reports AutoGAN checkpoint configuration status.
- Optional dependency group `autogan` adds modern Torch/Torchvision without changing core CI dependencies.

### Forensic policy
- AutoGAN is treated as a GAN-upsampling artifact family, not a universal AI detector.
- Descriptive AutoGAN features do not create an evidence family by themselves.
- Unvalidated checkpoints remain screening observations only.
- Negative AutoGAN results do not exclude GAN generation, diffusion models or other synthetic-media families.
- The canonical GT regression gate remains 100% mandatory and separate from population-level scientific validation.

## 0.7.0 - 2026-09-08

### Added
- Visual-artifact renderer writing derivative PNGs under `case/visuals/`.
- Image artifacts: amplified ELA, noise residual, FFT spectrum, RGB histogram, JPEG Ghost curve, resampling autocorrelation, copy-move overlay, face-context overlay, synthetic feature profile and reference-difference map.
- Video artifacts: frame-transition timeline, optical-flow timeline and signaled keyframe contact sheet.
- New `Gráficos e imagens` tab in the existing interactive report without redesigning its visual identity.
- `Apêndice A — Artefatos Visuais das Análises` in DOCX and Markdown reports with captions and method limitations.
- Artifact metadata and paths in each file report, with a safe local web route for viewing the generated PNGs.
- Tests for artifact generation, web serving and DOCX appendix embedding.

### Changed
- Report schema bumped to `0.6`.
- New v0.6 synthetic-media methods now have friendly labels and concise summaries in the report generator.
- Web version label is sourced from package metadata instead of being hardcoded.

### Forensic policy
- Visual artifacts are derivative inspection/documentation aids; they do not create an independent evidence family and do not increase evidentiary weight by themselves.
- Existing GT regression and MFLAB-DF evidentiary safeguards remain unchanged.

## 0.6.0 - 2026-09-08

### Added
- Explainable synthetic-media feature bank: multiband FFT, Haar-wavelet energies, HOG, RGB correlations, GLCM/LBP and color moments.
- Face-versus-context consistency screening for local facial replacement.
- Optional handcrafted ML detector bundle with explicit validation/calibration metadata.
- Optional ONNX deep-detector adapter without bundled unvalidated weights.
- Conservative cross-family synthetic evidence convergence summary.
- Scientific validation layer `MFLAB-SCI-SYNTH-0.2`, separate from regression CI.
- Scientific benchmark metrics including FPR, specificity, ROC-AUC, PR-AUC and Brier score, grouped by generator/transform and optional leave-one-generator-out.
- Model selection isolated from the final test set through an explicit validation split or stratified cross-validation on training data.

### Changed
- Deepfake protocol upgraded to `MFLAB-DF-0.5`.
- `deepfake`/`full` profiles now execute the new feature bank, face-context screen, optional ML/deep adapters and evidence fusion.
- Project version bumped to 0.6.0; scikit-learn added to core dependencies and ONNX Runtime exposed as optional `deep` dependency.
- Interactive site appearance intentionally unchanged; backend method results are extended only.

### Scientific policy
- Regression GT remains the mandatory deterministic CI oracle.
- Large-scale scientific validation is explicitly separate and must use external datasets/splits.
- Exported ML bundles default to `validated: false`; benchmark success alone does not grant forensic validity.

## 0.5.0 - 2026-09-08
- Interactive HTML forensic report, strict CI/CD, canonical independent ground truth and packaging/release gates.

## 0.4.0 - 2026-09-08
- Synthetic fixtures, reference-assisted localization/alignment, motion discontinuity and C2PA marker fallback.

## 0.3.0 - 2026-09-08
- Controlled validation harness and calibrated screening semantics.

## 0.2.0 - 2026-09-08
- Expanded classical forensics and MFLAB-DF integration architecture.