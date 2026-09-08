# Media Forensics Lab (Python) - v0.4

Laboratório educacional/de pesquisa para **análise reproduzível de autenticidade, manipulação e mídia sintética (IA/deepfake)** em imagens e vídeos, com geração de **laudo técnico preliminar** e rastreabilidade método → referência bibliográfica.

> **Regra central:** o laboratório não transforma um escore isolado em conclusão pericial. ELA, histogramas, ruído, FFT, PRNU simplificado, detectores de IA e outros sinais são interpretados em conjunto com proveniência, estrutura, contexto e cadeia de custódia.

## O que mudou na v0.4

- protocolo `MFLAB-DF-0.4`;
- duas novas fixtures sintéticas: `img_007_deepfake_face.jpg` (substituição facial controlada usando doador gerado por IA) e `img_008_ai_generated.png` (cena integralmente gerada por IA; a fixture fonte é preservada em `dataset/fixtures` para regressão determinística);
- triagem facial registra descontinuidade de textura/borda na fixture de substituição facial, sem convertê-la em probabilidade de deepfake;
- `c2pa_inspect` possui fallback de leitura de marcadores C2PA/JUMBF quando `c2patool` não está instalado; esse fallback **não** valida assinatura criptográfica;
- triagem sintética combina relação de alta/baixa frequência com residual tipo PRNU em limiar de engenharia testado apenas na fixture AI empacotada;
- comparação assistida com imagem de referência para localizar regiões alteradas; na base demo ela localiza splice, inpainting e substituição facial;
- alinhamento temporal assistido com vídeo de referência para localizar segmento removido após re-encode;
- triagem cega de descontinuidade de movimento por fluxo óptico para saltos temporais/conteúdo;
- `mflab validate-demo` executa 16 checks controlados;
- leitura de imagens via OpenCV reforçada para caminhos Unicode no Windows;
- limitações explícitas: os novos checks de splice/inpainting/face replacement são, em parte, **reference-assisted** e não equivalem a detectores cegos validados em população real.

## Funcionalidades

| Família | MFLab nativo | Veritas opcional | Uso no pipeline |
|---|---:|---:|---|
| SHA-256 / integridade | ✅ | ✅ | preservação |
| Hash perceptual | ✅ | ✅ | similaridade/proveniência auxiliar |
| C2PA / Content Credentials | ✅ (marcador nativo; validação criptográfica com c2patool) | — | proveniência |
| EXIF / metadados | ✅ | ✅ | estrutura/origem auxiliar |
| ELA | ✅ | ✅ | triagem |
| Histograma RGB | ✅ | ✅ | triagem |
| Noise map / residual | ✅ | ✅ | triagem |
| JPEG Ghost | ✅ | ✅ | triagem de recompressão |
| Quantização JPEG | ✅ | ✅ | histórico de compressão |
| DCT | ✅ | ✅ | triagem |
| Copy-move | ✅ (ORB) | ✅ (blocos+DCT) | triagem/cross-check |
| PRNU | ✅ residual de triagem | ✅ residual de triagem | **não** atribuição de câmera nesta versão |
| FFT/frequência | ✅ | ✅ | triagem |
| Resampling | ✅ | ✅ | triagem |
| Esteganografia LSB | ✅ | ✅ | triagem |
| Deepfake/GAN heurístico | ✅, sem probabilidade | ✅, secundário | triagem |
| Deepfake aprendido | por resultados externos | DeepfakeBench | camada validada separada |
| Vídeo: timestamps/frames | ✅ | upstream é focado em imagem | análise temporal |
| Vídeo: transições abruptas | ✅ | — | triagem de overlay/corte |
| Vídeo: fluxo óptico | ✅ | — | triagem de descontinuidade de conteúdo |
| Comparação com referência | ✅ | — | localização assistida de alterações / alinhamento temporal |
| Harness de validação demo | ✅ | — | regressão controlada contra ground truth |
| Laudo DOCX/Markdown | ✅ | — | consolidação |

## Estrutura

```text
media-forensics-lab/
├── mf_lab/
│   ├── analysis/            # métodos nativos
│   ├── integrations/        # Veritas / DeepfakeBench / resultados externos
│   ├── report/              # gerador de laudo
│   └── pipeline.py
├── docs/
│   ├── DEEPFAKE_PROTOCOL.md
│   └── UPSTREAM_EVALUATION.md
├── scripts/
│   ├── build_demo_dataset.py
│   ├── fetch_external_tools.py
│   └── download_bibliography.py
├── tests/
├── dataset/demo/
├── dataset/fixtures/         # fontes controladas para reconstruir fixtures sintéticas
├── bibliography/
├── third_party/
└── case-2026-001/
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .[test]
```

Se o Windows apresentar erro de certificado TLS ao acessar o PyPI:

```powershell
pip install -r .\requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -e . --no-deps --no-build-isolation
```

Dependências de sistema recomendadas:

- `ffmpeg` / `ffprobe` — necessário para a análise completa de vídeo;
- `exiftool` — recomendado para metadados avançados;
- `c2patool` — recomendado para validação criptográfica de C2PA/Content Credentials. Sem ele, o MFLab apenas detecta a presença de marcadores embutidos.

Veja `docs/WINDOWS_SETUP.md` para a instalação completa no Windows.

## Dataset e testes

```bash
python scripts/build_demo_dataset.py
pytest -q
mflab validate-demo --out validation/demo_validation.json
```

`pytest` responde principalmente se as rotinas e regressões codificadas estão funcionando. `mflab validate-demo` confronta as saídas com o `dataset/demo/ground_truth.json`. Na v0.4 são 16 verificações controladas, incluindo as duas novas fixtures sintéticas.

O ground truth registra pristine, copy-move, splice, double JPEG, resampling, inpainting, substituição facial sintética, imagem integralmente gerada por IA, duplicação de frames, remoção de segmento e overlay. Alguns checks usam uma referência conhecida (`reference-assisted`). **Essa base pequena não estima sensibilidade, especificidade, FPR/FNR ou validade pericial real.** Ela serve para regressão de engenharia e coerência com transformações conhecidas.

## Perfis de análise

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

Cada arquivo gera `*.report.json`, depois consolidado em `case/report.json`. O laudo lê o consolidado automaticamente.

## Protocolo de deepfake

Leia `docs/DEEPFAKE_PROTOCOL.md`.

O resultado automático nativo mantém `evidentiary_conclusion: inconclusive`. Heurísticas não calibradas e marcadores C2PA não validados criptograficamente aparecem como `screening_observations`; não são convertidos automaticamente em veredito de deepfake/IA.

## DeepfakeBench

O projeto mantém integração desacoplada. Execute detectores no ambiente do DeepfakeBench, exporte os escores e importe-os em `external/deepfake_scores.json`; só marque `validated: true` após documentar validação aplicável ao domínio/caso.

## Bibliografia e laudo

`bibliography/references.yaml` associa métodos às fontes. O gerador do laudo estrutura identificação/objeto, material recebido, cadeia de custódia, metodologia, resultados, mídia sintética/deepfake, conclusão preliminar, quesitos, limitações e referências. Ele usa como base jurídica o art. 473 do CPC e os arts. 158-A a 158-F do CPP, sem substituir avaliação jurídica do caso concreto.

## Observação sobre PRNU

Nesta versão, `prnu_screen` produz somente residual de triagem. **Não chame isso de identificação de câmera.** Source-camera identification requer vários exemplares conhecidos, extração/normalização apropriada do fingerprint e estatística calibrada (por exemplo PCE), com validação documentada.

## Desenvolvimento

```bash
pytest -q
mflab integrations
```

O CI em `.github/workflows/ci.yml` testa Python 3.10, 3.11 e 3.12 em Windows e Ubuntu.
