# Media Forensics Lab (Python) - v0.7

Laboratório técnico e de pesquisa para análise reproduzível de integridade, proveniência, manipulação e mídia sintética/deepfake em imagens e vídeos. A v0.7 mantém a identidade visual da interface e acrescenta uma camada de **artefatos visuais explicáveis**, exibida no site e incorporada automaticamente ao laudo.

> Regra central: nenhum escore, heurística, mapa, gráfico ou modelo isolado é convertido automaticamente em conclusão pericial. O MFLab separa observações de triagem, modelos validados, proveniência, artefatos derivados e interpretação especializada.

## Novidades da v0.7

- geração automática de artefatos visuais por arquivo em `case/visuals/`;
- nova aba **Gráficos e imagens** no laudo interativo, sem redesenhar o restante da interface;
- **Apêndice A — Artefatos Visuais das Análises** no DOCX e no Markdown;
- ELA visual amplificado, residual de ruído, espectro FFT e histograma RGB;
- curva JPEG Ghost e autocorrelação de reamostragem;
- overlay copy-move ORB quando há clusters suspeitos;
- overlay face versus contexto;
- perfil visual das novas features de mídia sintética (wavelet, FFT, correlação RGB, textura/HOG);
- mapa de diferença quando existe referência confiável correspondente;
- para vídeo: timeline de diferenças entre frames, timeline de fluxo óptico e contact sheet de frames sinalizados;
- metadados de cada artefato (`id`, método, categoria, legenda, limitação e caminho) gravados no `report.json`;
- nomes amigáveis e resumos das famílias novas da v0.6 integrados ao laudo;
- schema técnico do relatório atualizado para `0.6`.

Os artefatos são produtos derivados para inspeção e documentação. Uma área visualmente saliente **não aumenta por si só** o peso probatório do método que a originou.

## Capacidades de mídia sintética/deepfake

O protocolo permanece `MFLAB-DF-0.5` e combina:

1. integridade e proveniência (SHA-256, C2PA, metadados);
2. forense clássica (JPEG, ruído, resampling, PRNU-like, FFT etc.);
3. triagem facial e consistência face-contexto;
4. feature bank sintético (FFT + wavelet + HOG + RGB + GLCM/LBP);
5. ML handcrafted opcional e explicitamente configurado;
6. deep detector ONNX opcional e explicitamente configurado;
7. convergência entre famílias;
8. conclusão automática preservada como `evidentiary_conclusion: inconclusive` salvo raciocínio pericial documentado fora do escore automático.

Um score de modelo só entra como evidência validada quando a configuração/documentação do bundle o marca explicitamente como validado. Caso contrário permanece observação.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .[test]
```

No Windows, se houver problema TLS com PyPI:

```powershell
pip install -r .\requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -e . --no-deps --no-build-isolation
```

Opcional para detector profundo ONNX:

```powershell
pip install -e .[deep]
$env:MFLAB_SYNTHETIC_ONNX="C:\modelos\detector.onnx"
```

Dependências de sistema recomendadas: `ffmpeg`/`ffprobe`, `exiftool` e `c2patool`.

## Análise normal

```powershell
mflab analyze-file imagem.jpg --profile deepfake
mflab analyze-file imagem.jpg --profile full
mflab web
```

A interface local permanece em `http://127.0.0.1:8765`.

## Cases e artefatos visuais

```powershell
python scripts/make_case.py case-2026-001 --from-demo
mflab analyze-case case-2026-001 --profile full
mflab report case-2026-001 --format docx
mflab report case-2026-001 --format md
```

Estrutura relevante:

```text
case-2026-001/
├── original/
├── results/
├── visuals/
│   ├── img_001_pristine.jpg/
│   │   ├── ela.png
│   │   ├── noise_residual.png
│   │   ├── fft_spectrum.png
│   │   ├── rgb_histogram.png
│   │   └── synthetic_feature_profile.png
│   └── ...
├── final/
│   ├── case-2026-001_laudo_preliminar.docx
│   └── case-2026-001_laudo_preliminar.md
└── report.json
```

No site, a aba **Resumo e métodos** mantém a experiência anterior e a aba **Gráficos e imagens** mostra a galeria derivada. No DOCX, as mesmas figuras são inseridas no **Apêndice A**, com legenda e limitação metodológica.

## Validação nível 1 — CI/regressão

Continua obrigatória em cada mudança:

```powershell
python scripts/check_version.py
python -m compileall -q mf_lab scripts tests
python scripts/build_demo_dataset.py
git diff --exit-code -- dataset/demo/ground_truth.json
pytest -q
python scripts/ci_validate_gt.py --out validation/demo_validation.json
python -m pip check
```

O GT canônico exige 100% de cobertura e 100% de aprovação dos checks obrigatórios da base controlada. Esse 100% é regressão de engenharia, não acurácia universal.

## Validação nível 2 — benchmark científico

A validação científica usa datasets externos e explicitamente separados do CI. Exemplo de manifesto:

```csv
path,label,generator,split,transform
D:/datasets/real/001.jpg,real,camera,train,original
D:/datasets/stylegan3/001.png,synthetic,StyleGAN3,train,original
D:/datasets/real/101.jpg,real,camera,test,jpeg_q70
D:/datasets/progan/101.png,synthetic,ProGAN,test,jpeg_q70
```

Execute:

```powershell
mflab benchmark-synthetic .\benchmark\manifest.csv `
  --out .\validation\scientific\benchmark.json `
  --model-out .\models\synthetic_handcrafted.joblib `
  --cross-generator
```

O benchmark treina Logistic Regression, SVM-RBF, ExtraTrees e HistGradientBoosting sobre o feature bank, seleciona sem usar o test set final e registra desempenho global, por gerador, por transformação e leave-one-generator-out quando possível.

O bundle exportado é deliberadamente salvo com `validated: false`. Transformá-lo em modelo validado exige revisão do benchmark, splits independentes, ausência de leakage, cross-generator/cross-family, robustez a pós-processamento e critérios científicos documentados.

## Separação metodológica

- `dataset/demo` = regressão rápida e determinística do software;
- datasets científicos externos = estimativa de desempenho;
- `visuals/` = produtos derivados de inspeção, não um terceiro oráculo;
- validação cross-generator = treino em geradores conhecidos e teste em gerador não visto;
- validação cross-family = por exemplo GAN → diffusion;
- pós-processamento = JPEG, resize, blur, screenshot e reencode.

Nunca altere o ground truth apenas para fazer um detector passar.

## CI/CD e versionamento

O projeto usa SemVer, GitHub Actions em Windows/Ubuntu e Python 3.10–3.12, gate de GT, package smoke e release por tag. Consulte `docs/CI_CD.md`, `docs/SCIENTIFIC_VALIDATION.md` e `docs/VISUAL_ARTIFACTS.md`.
