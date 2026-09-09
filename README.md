# Media Forensics Lab (Python) - v0.6

Laboratório técnico e de pesquisa para análise reproduzível de integridade, proveniência, manipulação e mídia sintética/deepfake em imagens e vídeos. A v0.6 mantém a interface HTML da v0.5 sem alterações visuais e fortalece o backend analítico e a validação científica.

> Regra central: nenhum escore, heurística ou modelo isolado é convertido automaticamente em conclusão pericial. O MFLab separa observações de triagem, modelos validados, proveniência e interpretação especializada.

## Novidades da v0.6

- protocolo `MFLAB-DF-0.5`;
- banco de features sintéticas explicáveis: FFT multibanda, Haar-wavelet multiescala, HOG, correlações RGB, GLCM, LBP e momentos de cor;
- análise de consistência face-contexto para substituição facial;
- classificador ML opcional sobre features handcrafted, carregado apenas por bundle explicitamente configurado;
- adaptador opcional para detector profundo ONNX (`MFLAB_SYNTHETIC_ONNX`), sem embutir pesos não validados;
- resumo conservador de convergência entre famílias de evidência;
- segunda camada de validação científica, separada do CI, via `mflab benchmark-synthetic`;
- métricas de benchmark: accuracy, balanced accuracy, precision, sensitivity/recall, specificity, FPR, F1, ROC-AUC, PR-AUC e matriz de confusão;
- relatórios por gerador e por transformação, com opção leave-one-generator-out;
- suporte a robustez por coluna `transform` (JPEG, resize, screenshot, recompressão etc.);
- arquitetura preparada para comparação entre GANs, diffusion e outros geradores sem misturar benchmark científico com o GT de regressão.

A aparência do site permanece a mesma. Como a interface lista os métodos produzidos pelo pipeline, as novas análises aparecem nos detalhes e contribuem para a família “Sintético/deepfake” sem mudar o layout visual.

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

A interface local continua em `http://127.0.0.1:8765`.

### Pipeline de mídia sintética

Para imagens, a v0.6 combina:

1. integridade e proveniência (SHA-256, C2PA, metadados);
2. forense clássica (JPEG, ruído, resampling, PRNU-like, FFT etc.);
3. triagem facial e consistência face-contexto;
4. feature bank sintético (FFT + wavelet + HOG + RGB + GLCM/LBP);
5. ML handcrafted opcional e explicitamente configurado;
6. deep detector ONNX opcional e explicitamente configurado;
7. convergência entre famílias;
8. protocolo `MFLAB-DF-0.5`, mantendo `evidentiary_conclusion: inconclusive` automaticamente.

Um score de modelo só entra como evidência validada quando a configuração/documentação do bundle o marca explicitamente como validado. Caso contrário permanece observação.

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

A validação científica usa datasets externos e explicitamente separados do CI. Crie um CSV com:

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

O benchmark treina Logistic Regression, SVM-RBF, ExtraTrees e HistGradientBoosting sobre o feature bank, seleciona pelo balanced accuracy e registra desempenho global, por gerador, por transformação e leave-one-generator-out quando possível.

O bundle exportado é deliberadamente salvo com `validated: false`. Transformá-lo em modelo validado exige revisão do benchmark, splits independentes, ausência de leakage, cross-generator/cross-family, robustez a pós-processamento e critérios científicos documentados.

Para usar um bundle revisado no pipeline:

```powershell
$env:MFLAB_SYNTHETIC_MODEL="C:\modelos\synthetic_handcrafted.joblib"
mflab analyze-file imagem.jpg --profile deepfake
```

## Separação metodológica

- `dataset/demo` = regressão rápida e determinística do software;
- datasets científicos externos = estimativa de desempenho;
- validação cross-generator = treino em geradores conhecidos e teste em gerador não visto;
- validação cross-family = por exemplo GAN → diffusion;
- pós-processamento = JPEG, resize, blur, screenshot e reencode.

Nunca altere o ground truth apenas para fazer um detector passar.

## Laudo e interface

O DOCX/Markdown e o laudo interativo continuam sendo gerados pelo mesmo pipeline. As novas famílias aparecem como métodos adicionais no resultado técnico. O visual do site não foi redesenhado na v0.6.

```powershell
python scripts/make_case.py case-2026-001 --from-demo
mflab analyze-case case-2026-001 --profile full
mflab report case-2026-001 --format docx
mflab report case-2026-001 --format md
```

## CI/CD e versionamento

O projeto usa SemVer, GitHub Actions em Windows/Ubuntu e Python 3.10–3.12, gate de GT, package smoke e release por tag. Consulte `docs/CI_CD.md` e `docs/SCIENTIFIC_VALIDATION.md`.
