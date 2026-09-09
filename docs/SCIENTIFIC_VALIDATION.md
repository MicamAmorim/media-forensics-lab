# Validação científica de mídia sintética

A validação científica do MFLab é propositalmente separada do `dataset/demo` e do CI de regressão. Na v0.8 o protocolo é `MFLAB-SCI-SYNTH-0.3`.

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

`synthetic_handcrafted_v2` combina FFT multibanda, energias Haar-wavelet multiescala, HOG, correlação RGB, GLCM, LBP uniforme, momentos de cor e descritores espectrais AutoGAN-compatible. Essas features são descritivas. Um classificador só surge depois de treinamento em dataset explicitamente separado.

Os descritores AutoGAN incluem bandas full/low/mid/high, frações de energia, autocorrelação de perfis espectrais, lags de repetição e correlação entre quadrantes. Eles são tratados como features de artefatos associados a pipelines GAN com upsampling, e não como detector universal de IA.

## Modelos comparados

A implementação handcrafted compara Logistic Regression, SVM RBF, ExtraTrees e HistGradientBoosting. O modelo é selecionado por validação explícita ou cross-validation apenas no treino; o test set final permanece intocado até a avaliação.

Quando `MFLAB_AUTOGAN_CHECKPOINT` está configurado, um checkpoint ResNet34 AutoGAN-compatible é avaliado separadamente como detector fixo sobre o mesmo test set final. Esse checkpoint não participa da seleção do modelo handcrafted nem é retreinado no test set.

## Métricas

São registradas accuracy, balanced accuracy, precision, recall/sensitivity, specificity, false positive rate, F1, ROC-AUC, PR-AUC, Brier score quando há score contínuo e matriz de confusão.

Em aplicações forenses, FPR deve ser acompanhado explicitamente porque falso positivo implica classificar mídia real como sintética.

## Cross-generator e cross-family

Com `--cross-generator`, o benchmark executa uma forma leave-one-generator-out quando o manifesto contém grupos suficientes. Cross-family (por exemplo GAN → diffusion) deve ser estruturado usando famílias/geradores distintos e splits que impeçam leakage.

Para o ramo AutoGAN, a interpretação deve ser particularmente cuidadosa: o método foi concebido para artefatos de GANs. Portanto, GAN → diffusion é um teste de limite/generalização, e não um pressuposto de que o detector deva necessariamente transferir sem perda.

## Robustez

Use `transform` para versões JPEG, resize, blur, screenshot, reencode de rede social e outras transformações realistas. Métricas são reportadas por transformação. O checkpoint AutoGAN configurado também recebe métricas por transformação quando os subgrupos permitem avaliação.

## Deep learning

O pipeline possui um adaptador ONNX opcional e um adaptador opcional AutoGAN/ResNet34. Nenhum peso é embutido ou declarado validado por padrão. Modelos profundos devem documentar arquitetura/checkpoint, dataset de treino, splits, geradores vistos/não vistos, métricas globais/cross-generator, pós-processamento, calibração e hash do modelo.

O adaptador AutoGAN registra o SHA-256 do checkpoint. Um score só pode ser descrito como probabilidade calibrada se houver documentação independente de calibração no domínio de interesse.

## Interpretação

Um benchmark positivo valida desempenho somente no domínio declarado. Não estabelece validade universal ou admissibilidade pericial. A conclusão do caso continua exigindo proveniência, contexto, cadeia de custódia, convergência de métodos e interpretação especializada.

A regra continua sendo: `100%` no GT controlado significa regressão de engenharia perfeita contra aquele GT; não significa `100%` de acurácia forense no mundo real.
