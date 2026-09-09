# Validação científica de mídia sintética

A validação científica do MFLab é propositalmente separada do `dataset/demo` e do CI de regressão.

## Objetivo

Responder perguntas de desempenho que o GT pequeno não pode responder: generalização, sensibilidade, especificidade, falso positivo, desempenho fora do domínio, cross-generator, cross-family e robustez a pós-processamento.

## Manifesto

CSV mínimo:

```csv
path,label,generator,split,transform
/path/real1.jpg,real,camera,train,original
/path/fake1.png,synthetic,StyleGAN3,train,original
/path/real2.jpg,real,camera,test,jpeg_q70
/path/fake2.png,synthetic,ProGAN,test,jpeg_q70
```

Regras:

- `split` deve ser declarado antes da avaliação;
- identidades/cenas derivadas não devem vazar entre treino e teste;
- `generator` deve identificar a origem sintética quando conhecida;
- `transform` deve registrar pós-processamento;
- datasets externos não são commitados no repositório; versões, checksums e scripts de aquisição devem ser documentados.

## Feature bank

`synthetic_handcrafted_v1` combina FFT multibanda, energias Haar-wavelet multiescala, HOG, correlação RGB, GLCM, LBP uniforme e momentos de cor. Essas features são descritivas. Um classificador só surge depois de treinamento em dataset explicitamente separado.

## Modelos comparados

A primeira implementação compara Logistic Regression, SVM RBF, ExtraTrees e HistGradientBoosting.

## Métricas

São registradas accuracy, balanced accuracy, precision, recall/sensitivity, specificity, false positive rate, F1, ROC-AUC, PR-AUC e matriz de confusão.

Em aplicações forenses, FPR deve ser acompanhado explicitamente porque falso positivo implica classificar mídia real como sintética.

## Cross-generator e cross-family

Com `--cross-generator`, o benchmark executa uma forma leave-one-generator-out quando o manifesto contém grupos suficientes. Cross-family (por exemplo GAN → diffusion) deve ser estruturado usando famílias/geradores distintos e splits que impeçam leakage.

## Robustez

Use `transform` para versões JPEG, resize, blur, screenshot, reencode de rede social e outras transformações realistas. Métricas são reportadas por transformação.

## Deep learning

O pipeline possui um adaptador ONNX opcional. Nenhum peso é embutido ou declarado validado por padrão. Modelos profundos devem documentar arquitetura/checkpoint, dataset de treino, splits, geradores vistos/não vistos, métricas globais/cross-generator, pós-processamento, calibração e hash do modelo.

## Interpretação

Um benchmark positivo valida desempenho somente no domínio declarado. Não estabelece validade universal ou admissibilidade pericial. A conclusão do caso continua exigindo proveniência, contexto, cadeia de custódia, convergência de métodos e interpretação especializada.
