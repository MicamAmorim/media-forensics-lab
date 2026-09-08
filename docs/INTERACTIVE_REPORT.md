# MFLab v0.5 — Laudo interativo local

A v0.5 adiciona uma interface HTML local para análise visual de uma ou várias imagens. Ela não substitui o pipeline: a página chama as mesmas rotinas do MFLab, organiza os resultados em cartões, prévias e gráficos e oferece download do laudo DOCX, do Markdown e do JSON técnico.

## Executar

```powershell
mflab web
```

Depois abra `http://127.0.0.1:8765` no navegador. Para outra porta:

```powershell
mflab web --port 9000
```

Por segurança, o padrão é `127.0.0.1`, portanto a interface fica disponível apenas na máquina local. Não exponha o servidor em rede pública para analisar evidência real sem uma camada adequada de autenticação, TLS, controle de acesso e política de retenção.

## Fluxo

1. Arraste ou selecione até 50 imagens.
2. Escolha `quick`, `deepfake` ou `full`.
3. Clique em **Executar análise**.
4. A interface cria um caso temporário, calcula hashes e métodos do perfil, gera o `report.json` e o laudo preliminar.
5. Os resultados aparecem por arquivo, com prévia, SHA-256, resumo de triagem, gráfico de famílias de indicadores e detalhes expansíveis de cada método.
6. Use **Baixar laudo DOCX**, **Markdown**, **JSON técnico** ou **Imprimir / PDF**.

## Interpretação dos gráficos

As barras são **contagens de indicadores de triagem emitidos por famílias de métodos**. Não são probabilidades, porcentagens de falsificação, pesos de evidência ou calibração estatística. A conclusão probatória automática continua limitada pelo protocolo MFLAB-DF e pelos métodos efetivamente executados.

## Privacidade e retenção

Os uploads são gravados em um diretório temporário local (`mflab-web-runs`) para permitir análise e download do laudo. Na inicialização, execuções com mais de 24 horas são removidas. Para casos reais, preserve o original e a cadeia de custódia fora dessa interface e defina uma política explícita de retenção antes de uso operacional.
