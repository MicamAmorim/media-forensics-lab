# Media Forensics Lab v0.2 - release notes

This release turns the initial lab into a multi-family media-forensics pipeline with an explicit synthetic-media/deepfake protocol.

Key design choice: **no automatic AI verdict**. Native heuristics finish as screening/inconclusive. Learned detector evidence is imported separately and is only tagged as validated when the examiner documents that validation.

Third-party integration:
- CodeRafay/Forensic-Image-Analysis-Toolkit: optional BSD-3-Clause secondary cross-check, never executed by default.
- DeepfakeBench: optional learned-model backend; scores/checkpoints stay outside the native heuristic layer.
- TruFor: fetch hook retained for future localization integration.

Run:

```bash
pip install -e .[test]
python scripts/build_demo_dataset.py
pytest -q
mflab analyze-case case-2026-001 --profile full
mflab report case-2026-001 --format docx
```
