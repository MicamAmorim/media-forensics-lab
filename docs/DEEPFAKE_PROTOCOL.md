# MFLab Deepfake / Synthetic Media Protocol — MFLAB-DF-0.5

O protocolo evita uma única “probabilidade de IA”. A conclusão pericial deve combinar proveniência, histórico de codificação, análise clássica, features específicas de mídia sintética, modelos validados e revisão humana.

## Stage 0 — preservação e pergunta

1. preservar os bytes originais e calcular SHA-256;
2. registrar origem, transferência, aquisição e cadeia de custódia;
3. definir o problema: imagem integralmente sintética, face replacement/deepfake facial, vídeo manipulado, edição generativa local ou edição convencional.

## Stage 1 — proveniência

- C2PA/Content Credentials com `c2patool` quando disponível;
- comparação com arquivo/dispositivo fonte quando possível;
- metadados como evidência auxiliar, nunca como prova isolada.

## Stage 2 — forense clássica

- JPEG quantization, double JPEG/DCT e JPEG Ghost;
- ELA, histogramas e consistência de ruído;
- copy-move, resampling e domínio de frequência;
- residual PRNU-like apenas como triagem;
- vídeo: container/codec, timestamps/GOP, duplicações, transições e fluxo óptico;
- comparação assistida por referência quando uma referência confiável existe.

## Stage 3 — features específicas de mídia sintética

A v0.5 adiciona um banco explicável `synthetic_handcrafted_v1` com:

- FFT multibanda e razão alta/baixa frequência;
- energia Haar-wavelet em múltiplas escalas;
- HOG;
- correlações RGB;
- GLCM;
- LBP uniforme;
- momentos de cor.

Essas features são descritivas. Não existe um limiar universal que transforme uma feature em “imagem IA”.

Para faces, o protocolo mantém métricas faciais e adiciona comparação face-contexto de textura/ruído/sharpness. Essa comparação é não específica e pode ser afetada por iluminação, maquiagem, profundidade de campo, câmera e compressão.

## Stage 4 — ML handcrafted

O MFLab pode carregar um bundle Joblib por `MFLAB_SYNTHETIC_MODEL`. O bundle deve declarar `feature_names`, `estimator`, `model_name`, `calibrated`, `validated` e metadados de validação.

O MFLab não marca automaticamente bundles treinados localmente como validados. O benchmark científico exporta `validated: false` por padrão.

## Stage 5 — deep learning

Um detector profundo ONNX pode ser configurado por `MFLAB_SYNTHETIC_ONNX`. Nenhum checkpoint é embutido como “verdade” no repositório. Pesos profundos precisam documentar arquitetura, hash, treinamento, domínio, geradores vistos/não vistos, pós-processamento e calibração.

`MFLAB_SYNTHETIC_ONNX_VALIDATED=1` só deve ser usado depois de validação documental aplicável ao caso.

## Stage 6 — fusão/convergência

O MFLab resume famílias aparentemente independentes: espectral, facial, face-contexto, ruído, residual de sensor, proveniência e detectores aprendidos validados.

O resultado `convergence_level` serve para priorizar revisão. Ele **não** é probabilidade posterior e não assume independência estatística entre métodos.

## Stage 7 — decisão automática

A política permanece conservadora:

- heurísticas não calibradas → `screening_observations`;
- modelos configurados mas não validados → observações, nunca evidência final;
- modelos explicitamente validados → `evidence_families`, ainda dependentes de domínio/contexto;
- conclusão automática → `evidentiary_conclusion: inconclusive`.

## Validação em dois níveis

### Nível 1 — regressão CI

`mflab validate-demo` verifica a base controlada pequena e o contrato do ground truth. Serve para impedir regressões do software.

### Nível 2 — validação científica

`mflab benchmark-synthetic` usa datasets externos, splits declarados e métricas estatísticas. Serve para estimar desempenho, generalização e FPR.

A validação científica deve incluir, quando possível, within-domain, cross-generator, cross-family, JPEG/resize/screenshot/reencode, análise por gerador, matriz de confusão, sensitivity, specificity, FPR, ROC-AUC, PR-AUC e protocolo livre de leakage.

Consulte `docs/SCIENTIFIC_VALIDATION.md`.
