## Resumo

Descreva a mudança e o motivo.

## Validação

- [ ] `python scripts/check_version.py`
- [ ] `python scripts/build_demo_dataset.py`
- [ ] `pytest -q`
- [ ] `python scripts/ci_validate_gt.py --out validation/demo_validation.json`
- [ ] GT fixture coverage = 100%
- [ ] GT fixture pass rate = 100%
- [ ] GT assertion coverage = 100%
- [ ] GT assertion pass rate = 100%
- [ ] `gt_contract_errors = 0`
- [ ] nenhuma evidência real ou dado sensível foi adicionado ao repositório

## Impacto científico/pericial

Explique se a mudança altera detector, limiar, interpretação, esquema de saída, fixture ou alegação metodológica. Heurísticas de triagem não devem ser promovidas a conclusão evidenciária sem validação apropriada.

## Alteração de ground truth

- [ ] Não altera GT.
- [ ] Altera GT e o motivo científico/técnico está documentado abaixo.

Se o GT mudou, explique por que a expectativa anterior precisava mudar e quais checks foram atualizados. **Não ajuste o GT apenas para tornar um teste verde.**

## Versionamento

- [ ] A mudança cabe na versão atual em desenvolvimento; ou
- [ ] `pyproject.toml`, `CHANGELOG.md` e documentação de release foram atualizados de acordo com SemVer.
