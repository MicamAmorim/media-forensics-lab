# Windows setup and troubleshooting

## Recommended installation

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -e . --no-deps --no-build-isolation
python scripts/build_demo_dataset.py
pytest -q
```

The two-step installation is intentional. In networks that replace HTTPS
certificates, PEP 517 build isolation may try to create a temporary environment
and download `setuptools`/`wheel`, causing `CERTIFICATE_VERIFY_FAILED`.
Installing the build tools and runtime requirements first and then using
`--no-build-isolation --no-deps` avoids a second isolated download step.

`--trusted-host` is a workaround for networks with TLS inspection/self-signed
proxy certificates. Prefer installing the organization's CA certificate into
Python/pip's trust store when possible.

## Editable-install package discovery

MFLab uses a flat repository layout that also contains `dataset`, `templates`,
`third_party` and `bibliography`. These are not Python packages. The
`pyproject.toml` therefore explicitly restricts setuptools discovery to
`mf_lab*`, preventing setuptools from aborting with:

```text
Multiple top-level packages discovered in a flat-layout
```

## OpenCV version

MFLab v0.2 supports the stable OpenCV 4.x Python API and currently pins:

```text
opencv-python>=4.8,<5
```

If an OpenCV 5 preview wheel was previously installed, reinstall:

```powershell
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python
pip install "opencv-python>=4.8,<5" --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

## Paths containing accents

Some Windows/OpenCV builds fail to read image files through `cv2.imread` when
the path contains non-ASCII characters, e.g.:

```text
C:\Users\...\Perícia Digital\...
```

MFLab contains a Windows compatibility guard that reads the file through
Python/NumPy and decodes it with `cv2.imdecode`, preserving support for Unicode
paths without requiring the evidence directory to be renamed.

## Optional face cascade

Deepfake screening uses OpenCV's bundled Haar cascade only as an optional
face-region screening aid. If a particular OpenCV build does not expose the
legacy `CascadeClassifier` API, MFLab now disables that optional face screen
instead of aborting the full video/deepfake protocol.
