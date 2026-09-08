# Changelog

## 0.5.0 - 2026-09-08

### Added
- Local interactive HTML forensic report via `mflab web`.
- Drag-and-drop multi-image upload with profiles `quick`, `deepfake` and `full`.
- Responsive dashboard with image previews, SHA-256, triage state, per-family screening charts and expandable method results.
- Download actions for DOCX, Markdown and technical JSON, plus browser print/PDF mode.
- Temporary local case creation and cleanup of web runs older than 24 hours.
- Web smoke tests for index, health endpoint and multi-image upload contract.

### Safety and interpretation
- The web server binds to `127.0.0.1` by default.
- Charts show counts of screening indicators only; they are not probabilities, falsification percentages or evidentiary weights.
- The interface preserves the evidentiary safeguards of `MFLAB-DF-0.4` and does not turn native heuristics into automatic verdicts.

## 0.4.0 - 2026-09-08

### Added
- Two synthetic-media regression fixtures: controlled face replacement and a fully AI-generated natural-scene fixture; source fixtures are retained separately for deterministic rebuilds.
- Reference-assisted image difference localization for splice/inpainting/face replacement when a trustworthy reference exists.
- Reference-assisted video sequence alignment for deleted-segment detection.
- Optical-flow motion-discontinuity screening.
- Built-in non-cryptographic C2PA/JUMBF marker fallback when c2patool is absent.
- Windows setup guide.

### Changed
- Deepfake protocol bumped to MFLAB-DF-0.4.
- Face screening exposes controlled boundary/texture inconsistency flags without converting them into an evidentiary verdict.
- Case demo records reference mappings in case.yaml and the pipeline applies reference-assisted methods automatically.
- Unicode-safe image loading strengthened for Windows paths.

### Validation
- 31 automated tests pass in the v0.4 CI after fixture portability fixes.
- Demo validation: 16/16 required controlled checks pass, 0 failures.
- Important limitation: several new successes are reference-assisted or provenance-based; they do not establish reference-free population-level deepfake accuracy.

## 0.3.0 - 2026-09-08

### Added
- Controlled validation harness via `mflab validate-demo`.
- Exact fixture expectations for copy-move translation, duplicated-frame indices and overlay transition boundaries.
- Abrupt visual-transition screening for video.

### Changed
- Copy-move ORB now suppresses identity matches and clusters coherent translations.
- Deepfake protocol upgraded to MFLAB-DF-0.3: uncalibrated native heuristics are recorded as screening observations and cannot alone trigger a deepfake-specific escalation.
- Resampling screening uses short-lag persistence instead of treating raw lag-1 autocorrelation as discriminative.
- Preliminary report surfaces copy-move and abrupt-transition findings without falsely escalating pristine imagery as deepfake evidence.

## 0.2.0 - 2026-09-08

### Added
- MFLAB-DF-0.2 deepfake/synthetic-media protocol for images and videos.
- Native histogram, noise-map, JPEG Ghost, JPEG quantization, FFT, resampling, LSB steganalysis, perceptual hashes and PRNU-like residual screening.
- Optional C2PA inspection via `c2patool`.
- Optional CodeRafay/Veritas runtime adapter as a secondary cross-check.
- Optional DeepfakeBench integration via exported, explicitly validated model results.
- External model evidence schema at `case/external/deepfake_scores.json`.
- GitHub Actions CI for Python 3.10-3.12.
