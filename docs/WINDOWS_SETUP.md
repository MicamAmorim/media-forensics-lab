# MFLab v0.4 — instalação no Windows

## Obrigatório

1. **Python 3.10–3.12 (64-bit)**. Marque **Add Python to PATH** no instalador.
2. **Git for Windows**, para `git pull`, branches e atualizações do projeto.
3. **FFmpeg**, incluindo `ffmpeg.exe` e `ffprobe.exe`, ambos acessíveis pelo `PATH`. Os testes e a análise de vídeo dependem do `ffprobe`; OpenCV também precisa conseguir decodificar os MP4.
4. **Microsoft Visual C++ Redistributable 2015–2022 (x64)**. É recomendável para as wheels nativas usadas por OpenCV/NumPy/SciPy.

## Recomendado para o pipeline completo

- **ExifTool** — amplia a inspeção de metadados. Sem ele, o MFLab ainda lê EXIF básico via Pillow.
- **c2patool** — valida criptograficamente Content Credentials/C2PA. Sem ele, a v0.4 só detecta marcadores C2PA/JUMBF e deixa explícito `cryptographically_validated: false`.

## Opcional

- **NVIDIA CUDA** — somente se você decidir executar modelos aprendidos de deepfake em GPU (por exemplo, DeepfakeBench). O pipeline nativo não exige CUDA.
- **Visual Studio Build Tools** — normalmente não é necessário quando o pip encontra wheels prontas, mas pode ser exigido por alguma dependência externa/experimental compilada.
- **Microsoft Word ou LibreOffice** — apenas para abrir/inspecionar manualmente os laudos DOCX; não é necessário para gerá-los.

## Instalação do ambiente Python

No PowerShell, dentro do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps --no-build-isolation
```

Se sua rede apresentar erro de certificado TLS no PyPI:

```powershell
python -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
python -m pip install -e . --no-deps --no-build-isolation
```

## Verificações rápidas

```powershell
python --version
git --version
ffmpeg -version
ffprobe -version
exiftool -ver
c2patool --version
```

`exiftool` e `c2patool` podem estar ausentes sem impedir os testes nativos; o relatório indicará a limitação correspondente.

## Teste completo

```powershell
python scripts/build_demo_dataset.py
pytest -q
mflab validate-demo --out validation/demo_validation.json
```

Para criar um caso demo completo:

```powershell
python scripts/make_case.py case-2026-001 --from-demo
mflab analyze-case case-2026-001 --profile full
mflab report case-2026-001 --format docx
```
