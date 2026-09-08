# Publicação no GitHub

Este ambiente não possui acesso de escrita ao GitHub, então a publicação final deve ser feita localmente.

## Opção 1 — via git

```bash
cd media-forensics-lab
bash scripts/push_to_existing_repo.sh https://github.com/MicamAmorim/media-forensics-lab.git main
```

## Opção 2 — manual

```bash
cd media-forensics-lab
git init -b main
git add .
git commit -m "feat: Media Forensics Lab v0.2"
git remote add origin https://github.com/MicamAmorim/media-forensics-lab.git
git push -u origin main
```

## Observações
- Se o GitHub pedir autenticação, use seu token pessoal ou o login do GitHub Desktop.
- Se o repositório já tiver um README criado pelo GitHub e o push falhar por histórico divergente, faça:

```bash
git pull origin main --allow-unrelated-histories
# resolva conflito se houver
git push -u origin main
```
