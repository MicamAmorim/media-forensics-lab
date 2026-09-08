# Media Forensics Lab (Python) - v0.3

Laboratório educacional/de pesquisa para **análise reproduzível de autenticidade, manipulação e mídia sintética (IA/deepfake)** em imagens e vídeos, com geração de **laudo técnico preliminar** e rastreabilidade método → referência bibliográfica.

> **Regra central:** o laboratório não transforma um escore isolado em conclusão pericial. ELA, histogramas, ruído, FFT, PRNU simplificado, detectores de IA e outros sinais são interpretados em conjunto com proveniência, estrutura, contexto e cadeia de custódia.

## O que mudou na v0.3

- protocolo `MFLAB-DF-0.3`: heurísticas nativas não calibradas passam a ser **observações de triagem**, sem elevar por si só o caso a evidência de deepfake;
- correção do copy-move ORB: auto-matching deixa de ser bloqueado por identidade e passa a usar vizinhos não-idênticos + agrupamento geométrico por translação;
- detector de transições visuais abruptas em vídeo para triagem de overlays/cortes;
- resampling passa a expor persistência de autocorrelação de curto lag em vez de tratar correlação de lag 1 como discriminativa;
- `mflab validate-demo`: harness de validação regressiva contra o `ground_truth.json` controlado;
- ground truth enriquecido com translação conhecida do copy-move, índices exatos de frames duplicados e fronteiras do overlay;
- testes passam a verificar **detecção conhecida**, e não apenas se a função executou;
- lacunas atuais são registradas explicitamente como `unsupported` em vez de serem escondidas: localização de splice, inpainting e deleção de segmento após re-encode;
- permanecem as integrações opcionais com C2PA, DeepfakeBench e CodeRafay/Veritas.

## Funcionalidades

| Família | MFLab nativo | Veritas opcional | Uso no pipeline |
|---|---:|---:|---|
| SHA-256 / integridade | ✅ | ✅ | preservação |
| Hash perceptual | ✅ | ✅ | similaridade/proveniência auxiliar |
| C2PA / Content Credentials | ✅ | — | proveniência criptográfica |
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

- `ffmpeg` / `ffprobe`;
- `exiftool`;
- `c2patool` para C2PA/Content Credentials.

## Dataset e testes

```bash
python scripts/build_demo_dataset.py
pytest -q
mflab validate-demo --out validation/demo_validation.json
```

`pytest` responde principalmente se as rotinas e regressões codificadas estão funcionando. `mflab validate-demo` confronta as saídas do pipeline com o `dataset/demo/ground_truth.json` e informa separadamente checks aprovados, falhos e capacidades ainda não implementadas.

O ground truth registra adulterações controladas: copy-move, splice, double JPEG, resampling, inpainting, duplicação de frames, remoção de segmento e overlay. **Essa base pequena não estima sensibilidade, especificidade, FPR/FNR ou validade pericial real.** Ela serve para regressão de engenharia e coerência com manipulações conhecidas.

Para um pequeno conjunto externo AI-vs-real, em ambiente com Internet:

```bash
pip install -e .[ai]
python scripts/download_ai_samples.py --n-per-class 12
```

Datasets externos e pesos não são versionados no Git.

## Perfis de análise

```bash
mflab analyze-file imagem.jpg --profile quick
mflab analyze-file imagem.jpg --profile deepfake
mflab analyze-file imagem.jpg --profile full
```

- `quick`: preservação + proveniência + triagem compacta;
- `deepfake`: todas as famílias relevantes ao protocolo de mídia sintética;
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

O pipeline segue, em alto nível:

```text
preservação/hash
      ↓
C2PA + metadados + estrutura
      ↓
compressão / ruído / frequência / resampling / PRNU-residual
      ↓
face/temporal screening
      ↓
modelos aprendidos validados (quando configurados)
      ↓
convergência + revisão humana
      ↓
conclusão documentada
```

O resultado automático nativo mantém `evidentiary_conclusion: inconclusive`. Heurísticas não calibradas podem aparecer em `screening_observations`, mas não acionam sozinhas `needs_expert_review`. Isso é intencional: o raciocínio pericial final pertence ao examinador e precisa considerar validação do método e o contexto do caso.

### Importar resultados de modelos aprendidos

Crie:

```text
case-2026-001/external/deepfake_scores.json
```

Exemplo:

```json
{
  "files": {
    "questioned.mp4": [
      {
        "model": "FTCN",
        "score": 0.82,
        "label": "fake",
        "validated": true,
        "validation": "protocolo cross-dataset documentado no anexo",
        "checkpoint": "sha256:..."
      }
    ]
  }
}
```

`validated: true` deve ser colocado pelo examinador **somente após documentar a validação aplicável ao caso**.

## DeepfakeBench

O projeto não copia o DeepfakeBench para dentro do código principal. Em vez disso, mantém uma integração desacoplada, pois o framework possui ambiente, pesos, datasets e condições de licença próprios.

```bash
python scripts/fetch_external_tools.py deepfakebench
mflab integrations
```

Execute os detectores no ambiente do DeepfakeBench, exporte os escores e importe-os no arquivo `external/deepfake_scores.json`. Isso mantém a versão/checkpoint do modelo separada das heurísticas nativas.

## CodeRafay / Veritas

A revisão do repositório está em `docs/UPSTREAM_EVALUATION.md`.

A licença upstream é BSD 3-Clause. Por padrão o MFLab **não copia nem executa** código de terceiros. Para instalar o checkout:

```bash
python scripts/fetch_external_tools.py veritas
mflab integrations
```

Para executar todos os módulos upstream como **cross-check secundário**:

```bash
mflab analyze-case case-2026-001 --profile full --veritas
```

Os resultados ficam separados em `veritas_upstream_crosscheck`; nunca são fundidos silenciosamente em um “authenticity score”. O `third_party/CodeRafay-Veritas-NOTICE.md` preserva a atribuição/licença.

## Bibliografia

`bibliography/references.yaml` associa cada método às fontes pertinentes. O laudo importa automaticamente apenas as referências dos métodos executados, além da base legal/metodológica.

```bash
python scripts/download_bibliography.py
```

O script não contorna paywalls. Livros comerciais são apenas referenciados e **não** redistribuídos.

## Base do laudo

O gerador foi estruturado com:

- identificação/objeto;
- material recebido e SHA-256;
- cadeia de custódia/preservação;
- metodologia;
- resultados;
- protocolo de mídia sintética/deepfake;
- conclusão preliminar;
- respostas aos quesitos;
- limitações;
- referências.

Ele usa como base jurídica o art. 473 do CPC e os arts. 158-A a 158-F do CPP, sem substituir a avaliação jurídica do caso concreto.

## Observação sobre PRNU

Nesta versão, `prnu_screen` produz somente um residual de triagem. **Não chame isso de identificação de câmera.** Uma implementação pericial de source-camera identification deve usar vários exemplares conhecidos, extração/normalização apropriada do fingerprint e estatística calibrada (por exemplo PCE), com validação documentada.

## Desenvolvimento

```bash
pytest -q
mflab integrations
```

O CI em `.github/workflows/ci.yml` testa Python 3.10, 3.11 e 3.12.
