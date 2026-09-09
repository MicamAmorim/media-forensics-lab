# Changelog

## 0.9.1 - 2026-09-09

### Added
- Native C2PA validation through the official `c2pa-python` SDK, with `c2patool` compatibility fallback and marker-only fallback as a last resort.
- Explicit C2PA validation fields for active manifest, signature validation, asset data-hash validation, validation failures and producer hint.
- Regression fixture for a controlled OpenAI-generated image that produced a CIFAKE false-negative while independent forensic screening families converged.
- Regression tests preserving the distinction between a wrong machine `real` vote, expert-review escalation and an `inconclusive` evidentiary conclusion.

### Changed
- Project version bumped to `0.9.1`.
- Moderate or high convergence across independent screening families now triggers `needs_expert_review` even when no learned model is validated for the input.
- Cross-family review escalation remains prioritization only: it does not populate validated evidence families and does not create a synthetic/deepfake verdict.
- C2PA cryptographic integrity is now kept separate from certificate trust and from truthfulness of the depicted content.

### Fixed
- Preliminary reports no longer say that zero protocols require expert review when the synthetic-evidence fusion explicitly reports moderate/high convergence for expert review.
- Railway/web deployments no longer depend on an external `c2patool` executable to perform C2PA manifest validation when the Python SDK can read the asset.

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
- Synthetic evidence fusion that summarizes convergence across independent signal families without producing an evidentiary verdict.
- `MFLAB-DF-0.5` integration for synthetic feature/model outputs and face-context screening.
- Scientific validation protocol `MFLAB-SCI-SYNTH-0.2` supporting a development split and a locked final test split.
- Optional Kaggle CIFAKE downloader for external real-vs-AI benchmarking.
- Tests for feature stability, ML semantics, fusion policy and protocol integration.

### Changed
- Project version bumped to `0.6.0`.
- Deepfake profile now includes the synthetic feature bank, optional learned detectors, face-context consistency and evidence fusion.
- `MFLAB-DF` now consumes validated learned models as evidence only when their output explicitly declares `validated=true`.

### Forensic policy
- Handcrafted features and heuristic screens are not probabilities of AI generation.
- Unvalidated model outputs are screening only.
- Evidence fusion is a review-prioritization summary, not a posterior probability.
- Final synthetic-media claims require documented validation on the relevant domain and expert convergence.

## 0.5.0 - 2026-09-08

### Added
- Explicitly conservative video-authentication protocol with timestamp/GOP structure, duplicate-frame screening, abrupt-transition screening and optical-flow discontinuity screening.
- Adjacent duplicate-frame triage using normalized mean absolute difference.
- Robust abrupt-transition detection using a median/MAD threshold over frame-to-frame visual differences.
- Farneback optical-flow discontinuity screening with robust thresholding.
- Reference-assisted video alignment using constrained dynamic programming when a reference copy is available.
- Validation rule for `manipulated_interval` ground truth in synthetic/demo cases.

### Changed
- Project version bumped to `0.5.0`.
- Video protocol no longer treats a pHash anomaly count as a direct deepfake indicator.
- `video_deepfake_protocol` now consumes structural/temporal screening results and keeps `evidentiary_conclusion` conservative.
- Canonical validation now requires detection of a manipulated video interval while rejecting pristine/demo controls.

### Forensic policy
- Temporal anomalies can indicate editing, transcoding, packet loss or other non-malicious processing; they require corroboration.
- No single frame-level or temporal score is converted into a deepfake verdict.

## 0.4.0 - 2026-09-08

### Added
- Synthetic face-replacement and fully synthetic image fixtures with ground-truth masks and canonical validation expectations.
- Reference-assisted image localization with connected-component bounding boxes.
- Video segment-deletion fixture with manipulated-interval ground truth.
- Improved copy-move ORB detector with translation clustering and false-positive suppression.
- Expanded MFLAB-DF image protocol with face-region, spectral, noise, resampling, PRNU-like and C2PA screening families.

### Changed
- Project version bumped to `0.4.0`.
- Fixture generator now emits its own `generator.py` to make synthetic test data portable in CI.
- Canonical validation tolerances updated to capture intended manipulations without overclaiming forensic certainty.

### Forensic policy
- Native face/spectral/PRNU-like signals remain engineering triage, not validated deepfake-classifier evidence.
- C2PA/JUMBF marker presence is recorded as provenance screening when cryptographic validation is unavailable.
- Canonical CI validation is a regression gate on controlled fixtures, not a claim of population-level scientific accuracy.

## 0.3.1 - 2026-09-08

### Fixed
- Corrected source-file handling in `validate_ground_truth()` so expected ground-truth checks no longer re-analyze already-generated JSON reports.
- Canonical demo validation now passes on both pristine and manipulated image fixtures.

## 0.3.0 - 2026-09-08

### Added
- Ground-truth-aware validation gate with explicit TP/FP/FN/TN counts and per-case expectations.
- Canonical demo fixture metadata with pristine, manipulated and copy-move regions.
- CI gate for canonical ground-truth validation.

### Changed
- Demo fixture generator now creates deterministic pristine, splice and copy-move samples plus `ground_truth.json`.
- `validate` CLI supports `--ground-truth` and returns non-zero if canonical expectations fail.

## 0.2.0 - 2026-09-07

### Added
- Reference-assisted image comparison (`reference_image_difference`) with local difference metrics.
- Reference-assisted video alignment (`reference_video_alignment`) using sampled-frame pHash/DCT descriptors.
- Case schema supports per-file references through `case.reference_map`.
- Case-level `report.json` consolidating individual reports and validation status.
- Markdown and DOCX expert reports with method registry and source references.
- Optional CodeRafay/Veritas cross-check integration via isolated subprocess adapter.

### Changed
- Improved case analyzer with canonical result aggregation.
- Report generator now includes references needed by methods actually executed.

## 0.1.0 - 2026-09-07

### Added
- Initial reproducible case structure, image/video screening modules and CLI.
- SHA-256 integrity hashing, metadata, ELA, noise residual, histogram and perceptual hashes.
- Basic FFT/resampling/PRNU-like/copy-move/steganalysis screens.
- Preliminary Markdown/DOCX report generation with legal and scientific references.
