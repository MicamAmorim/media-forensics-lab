# MFLab v0.9 — classificação automática `real` / `synthetic`

A v0.9 introduz um voto computacional explícito de classe, separado da conclusão pericial.

## Modelo embarcado

O bundle `mflab_cifake_hgb_calibrated_v1.joblib` usa `synthetic_handcrafted_v2` (73 features) e um `CalibratedClassifierCV(HistGradientBoostingClassifier, method="sigmoid", cv=5)`.

A classe positiva é `synthetic`, com limiar padrão 0,5. O score retornado pelo classificador é interpretável como probabilidade calibrada **somente dentro do domínio de calibração/validação documentado**.

O bundle versionado, seus metadados e os artefatos científicos associados são regenerados pelo workflow reprodutível da v0.9; o CI geral permanece uma verificação independente de compatibilidade, testes, ground truth e empacotamento.

## Domínio validado

- Dataset: CIFAKE.
- Reais: CIFAR-10.
- Sintéticas: Stable Diffusion v1.4.
- Resolução: 32×32.
- Holdout primário fresco: 10.000 imagens, não utilizado no ajuste do modelo.
- Conjunto de ajuste: 90.000 imagens.

Resultados do holdout primário:

- accuracy: 92,42%;
- sensibilidade: 92,62%;
- especificidade: 92,22%;
- FPR: 7,78%;
- ROC-AUC: 0,9784;
- PR-AUC: 0,9787;
- Brier score: 0,05619.

## Política de decisão

O protocolo `MFLAB-DF-0.7` expõe:

```json
{
  "machine_assessment": {
    "label": "synthetic",
    "score_synthetic": 0.87,
    "decision_threshold": 0.5,
    "validated_for_input": false,
    "forensic_effect": "screening_only"
  },
  "evidentiary_conclusion": "inconclusive"
}
```

`machine_assessment.label` é o voto do classificador. `evidentiary_conclusion` continua sendo a conclusão de valor pericial e não é automaticamente substituída por `real` ou `synthetic`.

O modelo é marcado como validado no domínio CIFAKE, mas uma entrada arbitrária não é presumida como pertencente a esse domínio. A variável `MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED=1` existe para uso do examinador quando houver justificativa documental de compatibilidade do caso com o domínio validado. Mesma resolução, isoladamente, não basta.

## Limitações

Os resultados não estabelecem validade cross-generator ou cross-family. Eles não autorizam extrapolação automática para Midjourney, FLUX, DALL·E, SDXL, outros modelos de diffusion, GANs não vistos, face swap, vídeo ou evidência de alta resolução. Fora do domínio documentado, a classificação é triagem.

Consulte `validation/scientific/CIFAKE_V09_RESULT.json` e a seção de validação do `README.md` para os resultados e gráficos.
