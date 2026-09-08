# CI/CD, ground truth e versionamento

O MFLab usa GitHub Actions para impedir que alterações futuras sejam incorporadas sem regressão automatizada. O objetivo do pipeline é simples: **código novo só é considerado integrável quando a suíte automatizada, o contrato de ground truth e o empacotamento passam integralmente**.

## CI obrigatório

O workflow `.github/workflows/ci.yml` é executado em pull requests para `main` e em pushes para `main`.

A matriz cobre:

- Ubuntu + Python 3.10, 3.11 e 3.12;
- Windows + Python 3.10, 3.11 e 3.12.

Em cada combinação são executados, nesta ordem:

1. instalação limpa das dependências e do pacote em modo editável;
2. verificação de consistência da versão;
3. compilação sintática de `mf_lab`, `scripts` e `tests`;
4. reconstrução das fixtures controladas;
5. verificação de que o gerador **não alterou o ground truth canônico**;
6. `pytest -q`;
7. gate de GT com exigência exata de 100%;
8. `pip check`.

Cada ambiente publica `validation/demo_validation.json` como artifact por 30 dias. Depois da matriz, o pacote é construído como wheel/sdist, instalado e submetido a um smoke test do CLI. O job final `ci-gate` só fica verde quando a matriz e o empacotamento passaram.

## Ground truth como oráculo independente

`dataset/demo/ground_truth.json` é um arquivo versionado e independente. O script `scripts/build_demo_dataset.py` pode reconstruir imagens, máscaras e vídeos, mas **não pode reescrever o GT**. Essa separação evita um erro metodológico importante: o mesmo código que produz a amostra não pode atualizar silenciosamente a resposta esperada usada para julgá-la.

Cada fixture do GT possui `required_checks`. O validador exige simultaneamente:

- 100% das fixtures cobertas;
- 100% das fixtures aprovadas;
- 100% dos checks requeridos presentes;
- 100% dos checks requeridos aprovados;
- zero checks obrigatórios `unsupported`;
- zero erros de contrato GT;
- zero falhas.

O comando que reproduz o gate localmente é:

```bash
python scripts/build_demo_dataset.py
pytest -q
python scripts/ci_validate_gt.py --out validation/demo_validation.json
```

Adicionar uma nova fixture ao GT sem declarar e implementar checks obrigatórios faz o CI falhar. Adicionar um check de validação que não esteja declarado no GT também faz o contrato falhar. Isso mantém código e oráculo sincronizados de forma explícita.

> **Importante:** 100% de GT significa 100% de cobertura e aprovação contra esta base controlada. Não significa 100% de acurácia forense, sensibilidade, especificidade ou generalização para dados reais.

## Versionamento

O projeto segue SemVer (`MAJOR.MINOR.PATCH`).

- `PATCH`: correção compatível, sem mudança de API/contrato esperada;
- `MINOR`: funcionalidade nova compatível;
- `MAJOR`: mudança incompatível de API, esquema ou comportamento público.

Antes de uma release, a versão deve estar coerente em:

- `pyproject.toml`;
- seção correspondente de `CHANGELOG.md`;
- linha de release indicada no título do `README.md`;
- metadata carregada pelo pacote.

`scripts/check_version.py` falha se houver inconsistência. Em releases, a tag deve ser exatamente `v<versão>`, por exemplo `v0.5.0`.

## CD / releases

O workflow `.github/workflows/release.yml` dispara somente em tags `v*.*.*`.

Antes de publicar ele repete a matriz completa Windows/Ubuntu + Python 3.10/3.11/3.12, incluindo o gate de GT em 100%. Apenas depois disso:

1. constrói wheel e sdist;
2. gera `SHA256SUMS.txt`;
3. publica os artifacts do workflow;
4. cria uma GitHub Release com os arquivos construídos e notas automáticas.

Não há publicação automática no PyPI nesta etapa. Isso pode ser habilitado futuramente via Trusted Publishing, sem armazenar token estático no repositório.

## Regra recomendada para `main`

Para que o CI seja realmente impeditivo, a branch `main` deve usar proteção/ruleset no GitHub com, no mínimo:

- exigir pull request antes do merge;
- exigir o status check **`ci-gate`**;
- exigir branch atualizada antes do merge;
- exigir resolução de conversas;
- bloquear force-push;
- bloquear deleção da `main`;
- impedir bypass, exceto em procedimento administrativo documentado.

A configuração de proteção é uma configuração administrativa do repositório; ela não é aplicada apenas por versionar os arquivos de workflow.

## Dependências

`.github/dependabot.yml` abre PRs semanais para atualizações de dependências Python e GitHub Actions. Esses PRs passam pelos mesmos gates que qualquer outra alteração.

## Regra para alterações no GT

Mudanças em `ground_truth.json` devem ser tratadas como mudanças científicas, não como manutenção comum. O PR precisa explicar:

- por que a expectativa anterior estava incorreta ou por que a fixture mudou;
- qual método/transformação gera a nova expectativa;
- quais checks foram adicionados ou alterados;
- se a mudança altera apenas regressão de engenharia ou alguma alegação metodológica.

Nunca ajuste o GT apenas para fazer um detector novo passar.
