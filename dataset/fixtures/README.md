# Controlled synthetic fixture sources

This directory stores source material used only to rebuild the bundled regression fixtures.

- `face_donor_ai.png`: AI-generated donor portrait crop used to build `dataset/demo/images/img_007_deepfake_face.jpg`. The demo output changes only the face region of the pristine source via Poisson/seamless blending. This is a **controlled synthetic face-replacement fixture**, not a claim that it reproduces the artifact distribution of DeepFaceLab, FaceSwap, FaceForensics++ or another benchmark.
- `ai_generated_fixture.png`: fully AI-generated natural-scene fixture used directly to rebuild `dataset/demo/images/img_008_ai_generated.png`. It exercises signal/pixel screening only and is not presented as a representative benchmark sample.

These files exist for deterministic engineering regression. They do not establish real-world detector error rates.
