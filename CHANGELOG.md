# Changelog

## 0.3.0 - 2026-09-08

### Added
- Controlled validation harness via `mflab validate-demo`.
- Exact fixture expectations for copy-move translation, duplicated-frame indices and overlay transition boundaries.
- Abrupt visual-transition screening for video.

### Changed
- Copy-move ORB now suppresses identity matches and clusters coherent translations.
- Deepfake protocol upgraded to MFLAB-DF-0.3: uncalibrated native heuristics are recorded as screening observations and cannot alone trigger a deepfake-specific escalation.
- Resampling screening uses short-lag persistence instead of treating raw lag-1 autocorrelation as discriminative.
- Preliminary report now surfaces copy-move and abrupt-transition findings without falsely escalating pristine imagery as deepfake evidence.
- Project version bumped to 0.3.0.

### Validation
- 22 automated tests pass in the internal Linux environment.
- Demo harness: 9/9 required regression checks pass; 3 capability gaps are explicitly marked unsupported.
- Regenerated DOCX report rendered to 21 pages and visually reviewed; no clipping/overlap observed.

## 0.2.0 - 2026-09-08

### Added
- MFLAB-DF-0.2 deepfake/synthetic-media protocol for images and videos.
- Native histogram, noise-map, JPEG Ghost, JPEG quantization, FFT, resampling, LSB steganalysis, perceptual hashes and PRNU-like residual screening.
- Optional C2PA inspection via `c2patool`.
- Optional CodeRafay/Veritas runtime adapter as a secondary cross-check.
- Optional DeepfakeBench integration via exported, explicitly validated model results.
- External model evidence schema at `case/external/deepfake_scores.json`.
- GitHub Actions CI for Python 3.10-3.12.
- Upstream evaluation and third-party attribution notice.
- Expanded preliminary report section for synthetic media/deepfake analysis.

### Changed
- Report generator now distinguishes screening findings from evidentiary conclusions.
- PRNU is explicitly labelled as a screening residual, not source-camera attribution.
- Tables in DOCX reports repeat headers and avoid splitting rows when possible.
- Project version bumped to 0.2.0.

### Validation
- 12 automated tests pass on the bundled demo dataset.
- Demo case re-analyzed with the full v0.2 profile.
- Generated DOCX rendered to 18 pages and visually reviewed page-by-page.
