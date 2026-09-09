# MFLab Visual Forensic Artifacts — v0.7

## Objective

Visual artifacts are derivative products generated from the same media and numerical analyses already executed by MFLab. They exist to improve expert inspection, reproducibility, peer review and report communication. They are **not** an independent evidence family and must not be treated as stronger merely because a pattern looks visually salient.

## Storage and traceability

For a case, artifacts are written under:

```text
case-id/visuals/<media-name>/
```

Each per-file technical report contains `visual_artifacts.items[]` with:

- `id`: stable artifact identifier;
- `label`: human-readable title;
- `method`: analytic method that originated the visual;
- `category`: presentation grouping;
- `path`: path relative to the case root;
- `caption`: what is visualized;
- `warning`: method-specific limitation when applicable.

The original media SHA-256 remains the integrity anchor. PNG artifacts are derivatives and should not be confused with the acquired exhibit.

## Still-image artifacts

### ELA

Recompresses the RGB image at the quality used by the ELA method and renders the absolute difference with display amplification. Amplification is a visualization operation only. Different local intensities can result from ordinary JPEG history, texture, local contrast and processing.

### Noise residual

Displays the magnitude of a Gaussian high-pass residual after robust percentile normalization. It supports inspection of spatial consistency but is sensitive to texture, HDR, denoising, sharpening and recompression.

### FFT spectrum

Displays the centered log-magnitude 2-D Fourier spectrum. It supports inspection of periodic or generator/processing-dependent patterns but has no generator-independent decision threshold.

### RGB histogram

Plots per-channel intensity distributions. It is descriptive and can expose clipping or unusual channel distributions, not authenticity by itself.

### JPEG Ghost curve

Plots recompression error and local coefficient of variation across the quality sweep already used by the JPEG Ghost screen. A low-error quality can be compatible with prior JPEG compression, including benign processing.

### Resampling autocorrelation

Plots the X/Y derivative autocorrelation sequences used by the native resampling screen. The visual does not change the heuristic threshold or make it a calibrated detector.

### Copy-move overlay

When suspicious ORB translation clusters exist, draws source/destination bounding boxes and displacement vectors from the numeric cluster output. Repetitive textures and duplicated scene structures are known alternative causes.

### Face-context overlay

Draws the detected facial region and its comparison neighborhood, with noise/sharpness ratios used by the face-context screen. Lighting, makeup, depth of field and compression are alternative causes of mismatch.

### Synthetic feature profile

Creates four panels with their **own scales** for wavelet high-frequency energy, FFT multiband measurements, RGB correlations and selected texture/HOG features. It visualizes handcrafted features only and is not an AI probability.

### Reference difference

When a trusted corresponding reference is supplied, renders absolute difference as a heatmap and, when available, the largest changed component. Its value depends on the correspondence and provenance of the reference.

## Video artifacts

### Frame-transition timeline

Plots normalized frame-to-frame MAD and marks abrupt transitions and near-duplicates already identified by the temporal modules.

### Motion timeline

Plots mean Farnebäck optical-flow magnitude by transition and marks motion-discontinuity outliers.

### Keyframe contact sheet

Collects frames associated with temporal anomalies/duplicates into a compact inspection sheet. The sheet is a review aid, not a detector output independent from the temporal methods.

## Interactive report

The existing interface adds a `Gráficos e imagens` tab. Artifact PNGs are served only from the case `visuals/` directory through a path-checked local route. The overall visual language/layout is preserved.

## DOCX/Markdown report

The report generator appends:

```text
APÊNDICE A — ARTEFATOS VISUAIS DAS ANÁLISES
```

Figures are numbered `A.1`, `A.2`, ... and include the artifact label, caption and limitation. The appendix is documentation of the examination; it does not turn screening methods into validated evidence.

## Regression expectations

CI tests verify that:

1. core visual artifacts can be rendered from a controlled image;
2. artifact metadata paths point to existing files;
3. the web API serializes and serves artifact PNGs;
4. the DOCX contains the appendix heading and embeds at least one figure in the controlled report test;
5. the canonical demo GT remains unchanged and must still pass 100% independently of visual rendering.
