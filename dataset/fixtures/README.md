# Controlled synthetic fixture sources

This directory stores compact source material used only to rebuild the bundled regression fixtures.

- `face_donor_ai.jpg`: AI-generated donor portrait crop used to build `dataset/demo/images/img_007_deepfake_face.jpg`. The demo output changes only the face region of the pristine source via Poisson/seamless blending. This is a **controlled synthetic face-replacement fixture**, not a claim that it reproduces the artifact distribution of DeepFaceLab, FaceSwap, FaceForensics++ or another benchmark.
- `ai_generated_fixture.jpg`: compact AI-generated natural-scene source. The build script deterministically resizes it to 512×512 and writes `dataset/demo/images/img_008_ai_generated.png`. It exercises signal/pixel screening only and is not presented as a representative benchmark sample.

JPEG source fixtures are used deliberately to keep the repository small and to avoid fragile binary fixture transfers. The derived demo images are deterministic for regression purposes under the pinned image-processing stack, but the screening thresholds remain engineering checks rather than population-valid forensic classifiers.

These files exist for controlled engineering regression. They do not establish real-world detector sensitivity, specificity, FPR/FNR or courtroom validity.
