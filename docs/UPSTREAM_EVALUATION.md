# Evaluation of CodeRafay/Forensic-Image-Analysis-Toolkit (Veritas)

Repository reviewed: `CodeRafay/Forensic-Image-Analysis-Toolkit`.

## What is useful

The project is a well-organized educational/triage toolkit and exposes a broad set of image-forensic views: ELA, metadata, histogram, noise, JPEG ghost, quantization, copy-move, PRNU-like residuals, frequency analysis, deepfake/GAN heuristics, resampling, steganography and hash/provenance utilities. Its modular `analysis/` layout is useful as a secondary implementation for cross-checking MFLab results.

The upstream license is BSD 3-Clause, so redistribution/modification is allowed when its copyright notice, conditions and disclaimer are retained. MFLab therefore provides an **optional runtime adapter** and a fetch script rather than silently copying the source.

## Important technical cautions found during review

1. The upstream deepfake module explicitly describes itself as a simplified heuristic detector, not a professional deep-learning detector. MFLab agrees with that caveat and does not map those features to a forensic probability.
2. In the reviewed `detect_deepfake_artifacts` implementation, `img_array` is deleted before `img_array.shape` is used to build the result. That path can fail with an exception. This is a concrete reason not to make the upstream function the primary MFLab detector.
3. The PRNU module uses a Gaussian residual from a single/reference image and fixed correlation thresholds. That is educational screening, not the multi-image camera fingerprint/PCE workflow normally required for source-camera attribution.
4. The hash module calls a JSON record store a "simulated blockchain". It provides useful SHA-256/perceptual-hash bookkeeping, but it is not a distributed blockchain and should not be described as one in a forensic report.
5. Several techniques use fixed heuristic thresholds. Thresholds should be validated on a documented dataset before they are treated as decision rules in casework.

## Integration policy

- Native MFLab modules implement the forensic feature families with explicit `screening_only` warnings.
- `mf_lab.integrations.veritas` can load a local upstream checkout and run its implementations as a **secondary comparison**.
- Upstream results are stored distinctly as `upstream_result`; they are never silently blended into an MFLab evidentiary conclusion.
- Deepfake model evidence is handled separately through validated model adapters/exported results.
