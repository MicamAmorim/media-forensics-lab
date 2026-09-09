# Media Forensics Lab (Python) - v0.8

Laboratório técnico e de pesquisa para análise reproduzível de integridade, proveniência, manipulação e mídia sintética/deepfake em imagens e vídeos. A v0.8 preserva a interface visual da v0.7 e acrescenta uma implementação nativa, independente e compatível com a metodologia espectral do **AutoGAN** para análise de artefatos de upsampling em GANs.

> Regra central: nenhum escore, heurística, mapa, gráfico ou modelo isolado é convertido automaticamente em conclusão pericial. O MFLab separa observações de triagem, modelos validados, proveniência, artefatos derivados e interpretação especializada.

## Novidades da v0.8

- nova análise `autogan_spectral`, baseada no método de Zhang, Karaman e Chang (WIFS 2019);
- pré-processamento FFT por canal RGB com log-amplitude, normalização robusta P5/P95 e bandas `full`, `low`, `mid` e `high`;
- descritores de energia por banda, autocorrelação de perfis e correlação entre quadrantes, mantidos como features descritivas sem limiar universal de fake/real;
- feature bank sintético atualizado para `synthetic_handcrafted_v2`, incorporando as features AutoGAN-compatible;
- adaptador opcional para checkpoint ResNet34 compatível com o detector AutoGAN, sem incluir pesos arbitrários no repositório;
- metadados de validação/calibração permanecem obrigatórios para que um modelo deixe de ser apenas triagem;
- cinco novos artefatos visuais por imagem quando aplicável: espectro completo, bandas low/mid/high e perfil espectral descritivo;
- integração automática dessas figuras à aba **Gráficos e imagens** e ao **Apêndice A** do laudo, sem redesenhar a interface;
- benchmark científico atualizado para `MFLAB-SCI-SYNTH-0.3`, incluindo features AutoGAN-compatible e avaliação separada de um checkpoint AutoGAN configurado;
- protocolo de mídia sintética atualizado para `MFLAB-DF-0.6`;
- schema técnico do relatório atualizado para `0.7`.

A implementação espectral é uma reprodução independente da metodologia publicada. O MFLab não depende do ambiente antigo do repositório AutoGAN para executar a análise nativa.

## Capacidades de mídia sintética/deepfake

O protocolo `MFLAB-DF-0.6` combina:

1. integridade e proveniência (SHA-256, C2PA, metadados);
2. forense clássica (JPEG, ruído, resampling, PRNU-like, FFT etc.);
3. triagem facial e consistência face-contexto;
4. feature bank sintético (FFT + wavelet + HOG + RGB + GLCM/LBP + AutoGAN-compatible spectral descriptors);
5. análise GAN-específica de artefatos espectrais de upsampling inspirada no AutoGAN;
6. ML handcrafted opcional e explicitamente configurado;
7. deep detector ONNX opcional e explicitamente configurado;
8. checkpoint AutoGAN/ResNet34 opcional e explicitamente configurado;
9. convergência entre famílias;
10. conclusão automática preservada como `evidentiary_conclusion: inconclusive` salvo raciocínio pericial documentado fora do escore automático.

Um score de modelo só entra como evidência validada quando a configuração/documentação do bundle ou checkpoint o marca explicitamente como validado. Caso contrário permanece observação de triagem.

O AutoGAN é tratado como método de **GAN upsampling artifact detection**. Um resultado negativo não exclui geração por GAN e, sobretudo, não exclui diffusion ou outras famílias modernas de geração sintética.

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

Opcional para checkpoint AutoGAN-compatible:

```powershell
pip install -e .[autogan]
$env:MFLAB_AUTOGAN_CHECKPOINT="C:\modelos\autogan\checkpoint_10.pth"
$env:MFLAB_AUTOGAN_FEATURE_MODE="full"
```

Metadados opcionais do checkpoint podem ser fornecidos em um JSON lateral ou por:

```powershell
$env:MFLAB_AUTOGAN_METADATA="C:\modelos\autogan\checkpoint_10.json"
```

Exemplo de metadados:

```json
{
  "model_name": "autogan_resnet34_fft",
  "validated": false,
  "calibrated": false,
  "validation": {
    "protocol": "MFLAB-SCI-SYNTH-0.3",
    "report": "validation/scientific/autogan.json"
  }
}
```

Não marque `validated: true` apenas porque o modelo executa ou apresenta alta acurácia em um conjunto conhecido. A validação deve documentar domínio, splits independentes, FPR, sensibilidade, cross-generator/cross-family e robustez a pós-processamento.

Dependências de sistema recomendadas: `ffmpeg`/`ffprobe`, `exiftool` e `c2patool`.

## Análise normal

```powershell
mflab analyze-file imagem.jpg --profile deepfake
mflab analyze-file imagem.jpg --profile full
mflab integrations
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
│   │   ├── synthetic_feature_profile.png
│   │   ├── autogan_fft_full.png
│   │   ├── autogan_fft_low.png
│   │   ├── autogan_fft_mid.png
│   │   ├── autogan_fft_high.png
│   │   └── autogan_spectral_profile.png
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

O benchmark treina Logistic Regression, SVM-RBF, ExtraTrees e HistGradientBoosting sobre o feature bank ampliado, seleciona sem usar o test set final e registra desempenho global, por gerador, por transformação e leave-one-generator-out quando possível.

Se `MFLAB_AUTOGAN_CHECKPOINT` estiver configurado, o mesmo test set final também é usado para medir separadamente o checkpoint fixo AutoGAN-compatible, incluindo métricas globais e por gerador/transformação. Essa avaliação não treina o checkpoint no test set.

O bundle handcrafted exportado é deliberadamente salvo com `validated: false`. Transformá-lo em modelo validado exige revisão do benchmark, splits independentes, ausência de leakage, cross-generator/cross-family, robustez a pós-processamento e critérios científicos documentados.

## Separação metodológica

- `dataset/demo` = regressão rápida e determinística do software;
- datasets científicos externos = estimativa de desempenho;
- `visuals/` = produtos derivados de inspeção, não um terceiro oráculo;
- AutoGAN-compatible spectral analysis = família específica para artefatos de upsampling em GANs, não detector universal de IA;
- validação cross-generator = treino em geradores conhecidos e teste em gerador não visto;
- validação cross-family = por exemplo GAN → diffusion;
- pós-processamento = JPEG, resize, blur, screenshot e reencode.

Nunca altere o ground truth apenas para fazer um detector passar.

## CI/CD e versionamento

O projeto usa SemVer, GitHub Actions em Windows/Ubuntu e Python 3.10–3.12, gate de GT, package smoke e release por tag. Consulte `docs/CI_CD.md`, `docs/SCIENTIFIC_VALIDATION.md`, `docs/VISUAL_ARTIFACTS.md` e `docs/AUTOGAN_INTEGRATION.md`.
