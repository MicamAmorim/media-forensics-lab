# MFLab v0.7 — Laudo interativo local

A interface HTML local continua chamando as mesmas rotinas do MFLab e preserva sua identidade visual. A v0.7 acrescenta uma aba específica para os artefatos visuais derivados produzidos pelo pipeline.

## Executar

```powershell
mflab web
```

Depois abra `http://127.0.0.1:8765` no navegador. Para outra porta:

```powershell
mflab web --port 9000
```

Por segurança, o padrão é `127.0.0.1`, portanto a interface fica disponível apenas na máquina local. Não exponha o servidor em rede pública para analisar evidência real sem autenticação, TLS, controle de acesso e política de retenção.

## Fluxo

1. Arraste ou selecione até 50 imagens.
2. Escolha `quick`, `deepfake` ou `full`.
3. Clique em **Executar análise**.
4. A interface cria um caso temporário, calcula hashes e métodos do perfil, gera os artefatos em `visuals/`, o `report.json` e o laudo preliminar.
5. Em **Resumo e métodos**, veja a prévia, SHA-256, resumo de triagem, gráfico de famílias e detalhes de cada método.
6. Em **Gráficos e imagens**, veja a galeria de ELA, residual, FFT, histogramas, curvas, overlays e demais artefatos disponíveis para cada arquivo.
7. Use **Baixar laudo DOCX**, **Markdown**, **JSON técnico** ou **Imprimir / PDF**.

## Interpretação

As barras da aba de resumo são **contagens de indicadores de triagem**. Não são probabilidades, porcentagens de falsificação, pesos de evidência ou calibração estatística.

As imagens e gráficos da aba visual são **produtos derivados**. Eles ajudam a inspecionar e documentar o resultado numérico, mas não formam uma evidência independente e não devem ser interpretados como prova apenas porque uma região aparece destacada.

## DOCX

O laudo DOCX inclui automaticamente o **Apêndice A — Artefatos Visuais das Análises**. As figuras usam os mesmos artefatos exibidos no site, com título, legenda e limitação metodológica.

## Privacidade e retenção

Os uploads e derivados são gravados em um diretório temporário local (`mflab-web-runs`) para permitir análise e download do laudo. Na inicialização, execuções com mais de 24 horas são removidas. Para casos reais, preserve o original e a cadeia de custódia fora dessa interface e defina uma política explícita de retenção antes de uso operacional.
