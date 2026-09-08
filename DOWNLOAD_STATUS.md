# Status da bibliografia externa

O laboratório contém referências, URLs oficiais e `scripts/download_bibliography.py` para obter, diretamente das fontes, os documentos cuja redistribuição é permitida ou cuja página oficial oferece o arquivo.

Neste ambiente de geração do pacote, o acesso HTTP binário externo do container estava bloqueado. Por isso, os PDFs externos não foram falsamente marcados como baixados. Foram incluídos:

- excertos locais dos dispositivos legais relevantes (CPC, art. 473; CPP, arts. 158-A e seguintes), com URLs oficiais para os textos atualizados;
- manifesto `bibliography/references.yaml` com a bibliografia usada pelos métodos;
- notas de licenciamento/obtenção para fontes que não devem ser redistribuídas;
- script de download para execução em uma máquina com internet.

## Livros e materiais protegidos

Livros comerciais, como *Photo Forensics* de Hany Farid, são apenas referenciados. O projeto não copia ou contorna paywalls/licenças. Para esses itens, use biblioteca, compra, acesso institucional ou versão legal disponibilizada pelo autor/editora.

## Como baixar o que for legalmente disponível

```bash
python scripts/download_bibliography.py
```

Revise sempre a licença da fonte antes de redistribuir os PDFs baixados.
