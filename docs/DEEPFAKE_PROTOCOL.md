# MFLab Deepfake / Synthetic Media Protocol — MFLAB-DF-0.4

The protocol deliberately avoids a single "AI probability". A forensic conclusion should be based on provenance, file/encoding history, classical image/video forensics, validated learned detectors, and human review.

## Stage 0 — Preservation and question definition

1. Preserve original bytes and compute SHA-256.
2. Record source, transfer path, acquisition time and who handled the file.
3. Define the actual question: full synthetic image, face swap, reenactment, local generative edit, or ordinary editing.

## Stage 1 — Provenance

- C2PA / Content Credentials when present (`c2patool`).
- Original-source comparison and known-device samples when available.
- Metadata consistency is supporting evidence only.

## Stage 2 — Encoding and classical media forensics

- JPEG quantization / recompression / ghost screening.
- Histogram and noise-residual consistency.
- Copy-move, resampling and frequency-domain screening.
- PRNU-like residual screening; camera identification requires a calibrated multi-reference PRNU/PCE procedure.
- For video: container/codec, GOP/timestamps, missing/duplicated frames and transcode history.

## Stage 3 — Synthetic/deepfake screening

### Still images

- Spectral radial-profile / periodicity features.
- Face-region texture, boundary and luminance measurements when a face is present.
- Local noise/resampling/sensor-residual inconsistencies.

### Video

- Sampled face texture/luminance consistency.
- Sampled frequency consistency.
- Temporal structure and duplicate/gap analysis.

These native modules are **screening only**. In v0.4 their outputs are stored as `screening_observations`; because they are not calibrated to a target population/domain, they do **not** by themselves trigger `needs_expert_review` as deepfake evidence and do not produce an evidentiary AI probability.

## Stage 4 — Validated learned detectors

Preferred workflow:

1. Run more than one detector family using a benchmarked framework such as DeepfakeBench.
2. Record exact checkpoint, training dataset, preprocessing, threshold and software commit.
3. Prefer detectors evaluated cross-dataset, not only in-domain.
4. Keep frame-level and video-level outputs separate.
5. Export the scores to `case/external/deepfake_scores.json`; MFLab only marks a model output as validated when the examiner explicitly sets `validated: true` and documents the validation basis.

Example schema:

```json
{
  "files": {
    "questioned.mp4": [
      {
        "name": "FTCN",
        "score": 0.82,
        "threshold": 0.50,
        "decision": "fake",
        "validated": true,
        "dataset": "cross-dataset validation documented in case notes",
        "checkpoint": "sha256:...",
        "notes": "frame and video aggregation described in annex"
      }
    ]
  }
}
```

## Stage 5 — Convergence review

The examiner should ask whether apparently independent findings may share one cause (for example, WhatsApp recompression can affect noise, JPEG and spectral features together). Independence cannot be assumed just because different scripts produced different numbers.

Native MFLab heuristics end with `evidentiary_conclusion: inconclusive`. Uncalibrated screening observations remain distinct from validated evidence families. A stronger conclusion belongs in the examiner's reasoning, supported by documented validation and case context, not in an automatic score.

## Stage 6 — Report language

Preferred wording:

- "No strong screening signals were observed under the methods executed; this does not prove authenticity."
- "The file presents multiple findings that justify deeper examination."
- "Validated model X produced score Y under checkpoint/configuration Z."
- "The conclusion is based on convergence of A/B/C and is subject to the limitations listed."

Avoid:

- "97% AI, therefore fake."
- "ELA proves Photoshop."
- "Weak PRNU proves synthetic image."


## Controlled regression validation

Run:

```bash
mflab validate-demo --out validation/demo_validation.json
```

The bundled demo ground truth checks known injected transformations (for example copy-move translation and duplicated-frame positions) and verifies that the pristine fixture is not falsely escalated by the deepfake protocol. This is a **regression harness**, not a measurement of real-world sensitivity, specificity, false-positive rate or admissibility. Unsupported capabilities are reported explicitly rather than counted as successful detections.


## v0.4 controlled synthetic fixtures

The bundled regression set now contains a controlled face-replacement fixture and a fully AI-generated natural-scene fixture. The face fixture is created by blending an AI-generated donor face into the face region of the pristine source; it is **not** presented as a representative DeepFaceLab/FaceSwap benchmark sample. The full-AI fixture is used to exercise an uncalibrated signal-based synthetic-texture screen. Both source fixtures are retained under `dataset/fixtures/` for deterministic engineering regression.

Reference-assisted image comparison and video sequence alignment are separate capabilities: they are strong when a trustworthy corresponding reference exists, but they do not solve reference-free authentication. The native face-boundary and optical-flow rules remain uncalibrated screening heuristics.
