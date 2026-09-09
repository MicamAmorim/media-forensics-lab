# MFLab v0.9 — validação CIFAKE do classificador embarcado

- **Protocolo:** `MFLAB-SCI-CIFAKE-0.2`
- **Modelo:** `mflab_cifake_hgb_calibrated_v1`
- **Feature bank:** `synthetic_handcrafted_v2` (73 features)
- **Treino final:** 90,000 imagens CIFAKE
- **Holdout primário fresco:** 10,000 imagens do train original, escolhidas fora do subconjunto de desenvolvimento já inspecionado na v0.8
- **Teste oficial CIFAKE:** 20,000 imagens, reportado como avaliação secundária porque já havia sido inspecionado durante o desenvolvimento da v0.8

## Resultado primário — holdout fresco

| Métrica | Resultado |
|---|---:|
| Accuracy | 92.42% |
| Sensibilidade | 92.62% |
| Especificidade | 92.22% |
| FPR | 7.78% |
| ROC-AUC | 0.978396 |
| PR-AUC | 0.978665 |
| Brier | 0.056191 |

Matriz de confusão: TN=4611, FP=389, FN=369, TP=4631.

## Resultado secundário — teste oficial CIFAKE

| Métrica | Resultado |
|---|---:|
| Accuracy | 92.38% |
| Sensibilidade | 92.71% |
| Especificidade | 92.04% |
| FPR | 7.96% |
| ROC-AUC | 0.979180 |
| PR-AUC | 0.979465 |

## Limitação de validade

Este modelo é validado **somente no domínio declarado do CIFAKE**: CIFAR-10 real versus Stable Diffusion v1.4, resolução 32×32. Não há, nesta validação, suporte para generalizar as métricas a Midjourney, FLUX, DALL·E, SDXL, outros geradores, screenshots, pós-processamentos, fotografias reais de alta resolução, face swap ou vídeo. O voto `real`/`synthetic` permanece separado de `evidentiary_conclusion`.
