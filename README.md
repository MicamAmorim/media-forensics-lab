# Media Forensics Lab (Python) - v0.5

Laboratório educacional/de pesquisa para **análise reproduzível de autenticidade, manipulação e mídia sintética (IA/deepfake)** em imagens e vídeos, com geração de **laudo técnico preliminar**, **laudo interativo HTML local** e rastreabilidade método → referência bibliográfica.

> **Regra central:** o laboratório não transforma um escore isolado em conclusão pericial. ELA, histogramas, ruído, FFT, PRNU simplificado, detectores de IA e outros sinais são interpretados em conjunto com proveniência, estrutura, contexto e cadeia de custódia.

## O que mudou na v0.5

- nova interface local via `mflab web`, disponível por padrão em `http://127.0.0.1:8765`;
- importação por drag-and-drop de uma ou várias imagens;
- seleção dos perfis `quick`, `deepfake` e `full`;
- prévias, SHA-256, estado de triagem, gráficos por famílias de indicadores e detalhes expansíveis de cada método;
- botões para baixar o laudo em DOCX, Markdown e JSON técnico, além de impressão/PDF pelo navegador;
- interface responsiva sem CDN ou biblioteca gráfica externa;
- casos da interface são armazenados temporariamente na máquina local e execuções antigas são removidas na inicialização;
- os gráficos mostram **contagens de indicadores de triagem**, nunca probabilidades, percentuais de falsificação ou peso de evidência;
- toda a base analítica da v0.4 permanece presente, inclusive as fixtures de face replacement/IA, comparação assistida por referência e análise de descontinuidade de vídeo.

Documentação específica: `docs/INTERACTIVE_REPORT.md`.

## Recursos analíticos

| Família | MFLab nativo | Uso |
|---|---:|---|
| SHA-256 / integridade | ✅ | preservação |
| Hash perceptual | ✅ | similaridade/proveniência auxiliar |
| C2PA / Content Credentials | ✅ | marcador nativo; validação criptográfica com c2patool |
| EXIF / metadados | ✅ | estrutura/origem auxiliar |
| ELA / histograma / ruído | ✅ | triagem |
| JPEG Ghost / quantização / DCT | ✅ | compressão e recompressão |
| Copy-move ORB | ✅ | triagem geométrica |
| FFT / resampling | ✅ | triagem |
| PRNU-like residual | ✅ | triagem; **não** identificação de câmera |
| Esteganografia LSB | ✅ | triagem |
| Face / mídia sintética | ✅ | heurísticas não calibradas |
| Modelos aprendidos | externo | DeepfakeBench/resultados importados e validados separadamente |
| Vídeo: timestamps/duplicação/transições | ✅ | análise temporal |
| Vídeo: fluxo óptico | ✅ | triagem de descontinuidade de conteúdo |
| Comparação com referência | ✅ | localização assistida / alinhamento temporal |
| Harness `validate-demo` | ✅ | regressão controlada |
| Laudo DOCX/Markdown | ✅ | consolidação |
| Laudo interativo HTML | ✅ | exploração visual e download |

Integrações opcionais com CodeRafay/Veritas e DeepfakeBench permanecem desacopladas do núcleo.

## Estrutura

```text
media-forensics-lab/
├── mf_lab/
│   ├── analysis/            # métodos nativos
│   ├── integrations/        # Veritas / DeepfakeBench / resultados externos
│   ├── report/              # gerador DOCX/Markdown
│   ├── web/                 # HTML/CSS/JS do laudo interativo
│   ├── webapp.py            # servidor local Flask
│   └── pipeline.py
├── docs/
│   ├── DEEPFAKE_PROTOCOL.md
│   ├── INTERACTIVE_REPORT.md
│   ├── UPSTREAM_EVALUATION.md
│   └── WINDOWS_SETUP.md
├── scripts/
├── tests/
├── dataset/demo/
├── dataset/fixtures/         # fontes controladas das fixtures sintéticas
├── bibliography/
└── third_party/
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .[test]
```

No Windows, se houver erro TLS com o PyPI:

```powershell
pip install -r .\requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -e . --no-deps --no-build-isolation
```

Dependências de sistema recomendadas:

- `ffmpeg` / `ffprobe` — necessário para análise completa de vídeo;
- `exiftool` — recomendado para metadados avançados;
- `c2patool` — recomendado para validação criptográfica C2PA. Sem ele, o fallback nativo só detecta marcadores.

Veja `docs/WINDOWS_SETUP.md`.

## Laudo interativo

```powershell
mflab web
```

Abra:

```text
http://127.0.0.1:8765
```

A interface aceita até 50 imagens por execução e permite:

- arrastar/selecionar múltiplas imagens;
- escolher `quick`, `deepfake` ou `full`;
- executar o mesmo pipeline técnico do CLI;
- visualizar a imagem, SHA-256, resumo de triagem e gráficos por famílias de sinais;
- abrir os resultados de cada método;
- baixar **DOCX**, **Markdown** e **JSON técnico**;
- usar **Imprimir / PDF** para uma versão visual do laudo.

O servidor usa `127.0.0.1` por padrão para permanecer local. Não exponha o servidor à Internet para evidência real sem autenticação, TLS, controle de acesso e política de retenção adequados. Os uploads da interface são usados para criar casos temporários locais; execuções com mais de 24 horas são removidas na inicialização do servidor.

### Como interpretar os gráficos

As barras representam apenas **quantidade de indicadores de triagem emitidos por famílias de métodos**. Elas não representam probabilidade de falsificação, confiança estatística, peso probatório ou porcentagem de conteúdo gerado por IA.

## Dataset e validação

```bash
python scripts/build_demo_dataset.py
pytest -q
mflab validate-demo --out validation/demo_validation.json
```

A base controlada inclui:

- pristine;
- copy-move;
- splice;
- double JPEG;
- resampling;
- inpainting;
- substituição facial sintética;
- imagem integralmente gerada por IA;
- vídeo pristine;
- duplicação de frames;
- remoção de segmento;
- overlay.

Na v0.4, o harness contém 16 verificações controladas. Alguns checks de splice, inpainting, face replacement e remoção de segmento são **reference-assisted**. A base serve para regressão de engenharia e **não** estima sensibilidade, especificidade, FPR/FNR ou validade pericial em população real.

## Perfis

```bash
mflab analyze-file imagem.jpg --profile quick
mflab analyze-file imagem.jpg --profile deepfake
mflab analyze-file imagem.jpg --profile full
```

- `quick`: preservação + proveniência + triagem compacta;
- `deepfake`: famílias relevantes ao protocolo de mídia sintética;
- `full`: protocolo completo + copy-move + esteganálise e demais métodos nativos.

## Caso completo

```bash
python scripts/make_case.py case-2026-001 --from-demo
mflab analyze-case case-2026-001 --profile full
mflab report case-2026-001 --format docx
```

Cada arquivo gera `*.report.json`; o caso é consolidado em `report.json`, que alimenta o laudo.

## Protocolo de mídia sintética

Leia `docs/DEEPFAKE_PROTOCOL.md`.

O protocolo atual é `MFLAB-DF-0.4`. O resultado automático nativo mantém `evidentiary_conclusion: inconclusive`. Heurísticas não calibradas e marcadores C2PA não validados criptograficamente aparecem como observações de triagem; não são convertidos automaticamente em veredito de deepfake/IA.

A fixture `img_007_deepfake_face.jpg` é uma substituição facial **controlada**, não uma amostra representativa de DeepFaceLab/FaceSwap/FaceForensics++. `img_008_ai_generated.png` é uma fixture integralmente sintética para regressão. Nenhuma das duas, isoladamente, valida um classificador para uso real.

## DeepfakeBench / Veritas

O DeepfakeBench permanece desacoplado: execute os detectores no ambiente próprio, exporte os escores e importe-os em `external/deepfake_scores.json`. Só marque `validated: true` quando houver validação documentada aplicável ao domínio/caso.

O CodeRafay/Veritas pode ser usado como cross-check opcional:

```bash
python scripts/fetch_external_tools.py veritas
mflab analyze-case case-2026-001 --profile full --veritas
```

Resultados upstream permanecem separados e nunca são fundidos silenciosamente em um “authenticity score”.

## Bibliografia e laudo

`bibliography/references.yaml` associa métodos às fontes. O gerador estrutura identificação/objeto, material recebido, cadeia de custódia, metodologia, resultados, mídia sintética/deepfake, conclusão preliminar, quesitos, limitações e referências. A base jurídica inclui o art. 473 do CPC e os arts. 158-A a 158-F do CPP, sem substituir avaliação jurídica do caso concreto.

## PRNU

`prnu_screen` produz somente residual de triagem. **Não chame isso de identificação de câmera.** Source-camera identification exige vários exemplares conhecidos, fingerprint adequadamente extraído/normalizado e estatística calibrada, como PCE, com validação documentada.

## Desenvolvimento

```bash
pytest -q
mflab integrations
```

O CI testa Python 3.10, 3.11 e 3.12 em Windows e Ubuntu.
