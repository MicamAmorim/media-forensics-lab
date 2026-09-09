# Changelog

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
