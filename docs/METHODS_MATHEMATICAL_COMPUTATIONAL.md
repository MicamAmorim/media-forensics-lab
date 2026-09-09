# MFLab — Referência matemática e computacional dos métodos implementados

**Versão de referência:** MFLab v0.8.x  
**Protocolo de mídia sintética:** `MFLAB-DF-0.6`  
**Benchmark científico:** `MFLAB-SCI-SYNTH-0.3`

Este documento descreve, de forma sistemática, os principais métodos matemáticos e computacionais atualmente implementados no pipeline do Media Forensics Lab (MFLab). O objetivo é registrar **o que o código realmente calcula**, como cada resultado deve ser interpretado e quais são suas limitações.

> **Regra forense central:** um escore, mapa, gráfico, heurística ou classificador isolado não é convertido automaticamente em conclusão pericial. O MFLab separa integridade, proveniência, observações de triagem, modelos aprendidos, validação científica e interpretação especializada.

---

## 1. Visão geral do pipeline

Para imagens, os perfis `deepfake` e `full` executam, em termos gerais:

```text
arquivo
  ├─ SHA-256
  ├─ C2PA / Content Credentials
  ├─ metadados
  ├─ hashes perceptuais
  ├─ ELA
  ├─ residual de ruído / mapa de ruído
  ├─ histograma RGB
  ├─ FFT / frequência
  ├─ reamostragem
  ├─ PRNU-like
  ├─ análise facial
  ├─ face versus contexto
  ├─ triagem espectral sintética
  ├─ AutoGAN-compatible spectral analysis
  ├─ banco de características sintéticas v2
  ├─ ML handcrafted opcional
  ├─ detector ONNX opcional
  ├─ classificador AutoGAN/ResNet34 opcional
  ├─ JPEG: quantização / ghost / DCT, quando aplicável
  ├─ copy-move ORB, no perfil full
  ├─ LSB steganography screen, no perfil full
  ├─ comparação com referência, quando fornecida
  ├─ fusão conservadora de famílias
  └─ protocolo MFLAB-DF-0.6
```

Para vídeo, o pipeline combina metadados/container, timestamps, duplicação de frames, transições abruptas, fluxo óptico, comparação com referência e protocolo temporal/deepfake.

---

# PARTE I — INTEGRIDADE, PROVENIÊNCIA E METADADOS

## 2. SHA-256 — integridade criptográfica

### Implementação

O arquivo é lido em blocos e passado ao `hashlib.sha256`.

Matematicamente, SHA-256 produz:

\[
H : \{0,1\}^{*} \rightarrow \{0,1\}^{256}.
\]

O resultado é um digest de 256 bits, normalmente representado por 64 caracteres hexadecimais.

### Interpretação

Se dois arquivos possuem SHA-256 diferentes, os conteúdos binários são diferentes. Se o hash calculado no recebimento e o hash recalculado posteriormente coincidem, há forte suporte à integridade binária desde o ponto em que o primeiro hash foi obtido.

### O que SHA-256 não prova

SHA-256 **não prova autenticidade da cena**, autoria, origem da câmera ou ausência de manipulação anterior à aquisição. Ele prova integridade do arquivo em relação ao valor de referência.

---

## 3. C2PA / Content Credentials

O MFLab possui duas rotas.

### 3.1 Validação com `c2patool`

Quando `c2patool` está instalado, o MFLab solicita o manifesto em JSON. No estado atual do código, uma execução bem-sucedida e parseável é registrada como:

```text
cryptographically_validated = true
```

O resultado deve ser interpretado como evidência de **proveniência declarada/assinada**, não como detector de manipulação de pixels.

### 3.2 Fallback de marcadores

Sem `c2patool`, o MFLab faz apenas busca binária por marcadores associados a `c2pa` e `JUMBF`.

Nesse modo:

```text
cryptographically_validated = false
```

Mesmo que os marcadores existam, isso não equivale à verificação da assinatura, certificado ou cadeia de confiança.

---

## 4. Metadados

### Imagens

São lidos, quando disponíveis:

- formato;
- modo de cor;
- dimensões;
- EXIF via Pillow;
- dados adicionais via ExifTool, se instalado.

### Vídeos

O `ffprobe` fornece informações de container e streams, como codec, duração, parâmetros temporais e demais campos expostos pelo arquivo.

### Interpretação

Metadados são evidência contextual. Ausência ou inconsistência pode ser relevante, mas metadados podem ser removidos, reescritos ou recriados legitimamente.

---

# PARTE II — SIMILARIDADE E COMPRESSÃO

## 5. Hashes perceptuais: aHash, dHash e pHash

Hashes perceptuais servem para similaridade, não para integridade criptográfica.

### 5.1 aHash

A imagem em tons de cinza é redimensionada para \(8\times8\). Seja \(I_{ij}\) o valor de cada pixel e \(\bar I\) a média:

\[
b_{ij}=\begin{cases}
1,&I_{ij}\ge \bar I\\
0,&I_{ij}<\bar I.
\end{cases}
\]

Os 64 bits são codificados em hexadecimal.

### 5.2 dHash

A imagem é reduzida para \(9\times8\) e são comparados pixels adjacentes horizontalmente:

\[
b_{ij}=\mathbf 1[I_{i,j+1}\ge I_{i,j}].
\]

### 5.3 pHash

A imagem é redimensionada para \(32\times32\). O MFLab aplica DCT 2-D, retém o bloco \(8\times8\) de baixa frequência e compara os coeficientes com a mediana dos coeficientes sem a primeira linha:

\[
b_{uv}=\mathbf 1[C_{uv}\ge \operatorname{mediana}(C_{1:,:})].
\]

### Interpretação

Distâncias de Hamming pequenas entre hashes podem indicar imagens visualmente semelhantes mesmo após mudanças de tamanho ou compressão. Não são prova de identidade binária.

---

## 6. ELA — Error Level Analysis

A imagem é recomprimida em JPEG com qualidade padrão \(Q=90\), produzindo \(I_Q\). Calcula-se:

\[
D(x,y,c)=|I(x,y,c)-I_Q(x,y,c)|.
\]

O MFLab registra média absoluta e erro máximo. Na camada visual, a diferença é amplificada apenas para inspeção.

### Interpretação

Regiões com comportamento de recompressão distinto podem chamar atenção, porém textura, bordas, compressões anteriores, edição legítima e pipeline de redes sociais também alteram ELA.

**Status:** triagem exploratória.

---

## 7. JPEG Ghost

Para uma sequência de qualidades \(q\), por padrão de 55 a 100 em passos de 5, o MFLab recomprime a imagem e calcula o erro absoluto médio:

\[
E_q=\frac{1}{N}\sum_{x,y}\operatorname{mean}_c |I-I_q|.
\]

Também divide o mapa de diferença em blocos \(32\times32\) e calcula o coeficiente de variação local:

\[
CV_q=\frac{\sigma(E_{q,b})}{\mu(E_{q,b})+\varepsilon}.
\]

O menor \(E_q\) é registrado.

### Interpretação

Um mínimo de erro pode ser compatível com uma qualidade de compressão anterior, mas compressão anterior pode ser perfeitamente legítima.

---

## 8. Tabelas de quantização JPEG

Quando o arquivo é JPEG, o MFLab extrai as tabelas de quantização disponíveis. Para cada tabela \(Q\), registra:

\[
\sum_i Q_i,\qquad \bar Q,\qquad \min Q_i,\qquad \max Q_i,
\]

além dos primeiros 16 coeficientes.

### Interpretação

Tabelas podem ajudar a caracterizar histórico de codificação ou famílias de software, mas não identificam unicamente manipulação.

---

## 9. Periodicidade DCT / dupla compressão — heurística educacional

A imagem é dividida em blocos \(8\times8\). Para cada bloco, é aplicada DCT 2-D ortonormal e extraído o coeficiente \(C_{1,2}\).

Os coeficientes arredondados geram um histograma \(h_k\). O código calcula:

\[
z=\frac{\#\{k:h_k=0\}}{\#\{k\}},
\]

\[
a=\frac{\operatorname{mean}|h_{k+1}-h_k|}{\operatorname{mean}(h_k)+\varepsilon},
\]

\[
score=\min(1,\;0.5z+0.05a).
\]

### Interpretação

Esse `score` é um indicador heurístico de irregularidade/periodicidade no histograma DCT. Não é um detector publicado calibrado de dupla compressão.

---

# PARTE III — RUÍDO, SENSOR E REAMOSTRAGEM

## 10. Residual de ruído

A imagem em cinza normalizada \(I\in[0,1]\) é suavizada por filtro gaussiano \(G_\sigma\), com \(\sigma\approx1\):

\[
R=I-G_\sigma * I.
\]

São registrados:

\[
\mu_R,\qquad \sigma_R,
\]

além do desvio absoluto mediano:

\[
MAD_R=\operatorname{mediana}(|R-\operatorname{mediana}(R)|).
\]

---

## 11. Consistência local do mapa de ruído

No `noise_map_analysis`, usa-se \(\sigma=1.2\) e o residual é dividido em blocos de \(64\times64\). Para cada bloco \(b\):

\[
e_b=\operatorname{std}(R_b).
\]

Depois:

\[
CV_{ruido}=\frac{\operatorname{std}(e_b)}{\operatorname{mean}(e_b)+\varepsilon}.
\]

No protocolo de deepfake, atualmente:

\[
CV_{ruido}>0.75
\]

gera uma observação de triagem de alta variabilidade local de residual.

### Limitação

Textura da cena, HDR, denoising, sharpening e recompressão também alteram o residual.

---

## 12. PRNU-like residual screen

O MFLab implementa apenas uma triagem **PRNU-like**, e não uma atribuição de câmera completa por fingerprint/PCE.

Para cada canal:

\[
R_c=I_c-G_{\sigma=1}*I_c.
\]

O residual RGB é particionado em blocos e usa-se novamente a variabilidade da energia local:

\[
CV_{PRNU}=\frac{\sigma(e_b)}{\mu(e_b)+\varepsilon}.
\]

No protocolo:

\[
CV_{PRNU}>0.75
\]

é uma observação de triagem.

### Importante

Não há, nesse módulo, construção de fingerprint de câmera de referência nem cálculo de PCE. Portanto, ele não deve ser chamado de identificação de dispositivo fonte.

---

## 13. Reamostragem por segunda derivada e autocorrelação

O MFLab calcula derivadas de segunda ordem por Sobel:

\[
D_x=|\partial^2 I/\partial x^2|,\qquad D_y=|\partial^2 I/\partial y^2|.
\]

Após média na direção ortogonal, obtêm-se séries 1-D. Para uma série centralizada \(v\), a autocorrelação normalizada no lag \(\ell\) é:

\[
r(\ell)=\frac{\sum_i v_i v_{i+\ell}}{\sum_i v_i^2+\varepsilon}.
\]

A característica usada atualmente é a persistência curta:

\[
p=\frac{r(2)}{r(1)}.
\]

O maior valor entre X e Y é comparado ao limiar:

\[
p\ge0.94.
\]

### Interpretação

Esse limiar é uma heurística de triagem validada apenas no contexto de regressão controlada do projeto, não um detector universal de interpolação.

---

# PARTE IV — FREQUÊNCIA E TEXTURA

## 14. FFT bidimensional e perfil radial

Para imagem em cinza centralizada:

\[
X(u,v)=\mathcal F\{I-\bar I\}.
\]

O MFLab usa magnitude logarítmica:

\[
M(u,v)=\log(1+|\operatorname{fftshift}(X)|).
\]

O plano é dividido em 64 anéis radiais. Em cada anel calcula-se a média de \(M\), produzindo um perfil \(p_k\).

### Razão alta/baixa frequência

\[
R_{HL}=\frac{\operatorname{mean}(p_{3/4:})}{\operatorname{mean}(p_{1:1/4})+\varepsilon}.
\]

### Picos espectrais

Padroniza-se o perfil:

\[
z_k=\frac{p_k-\mu_p}{\sigma_p+\varepsilon}.
\]

Um bin interno é considerado pico quando:

\[
z_k>1.5,\qquad z_k>z_{k-1},\qquad z_k>z_{k+1}.
\]

### Simetria entre quadrantes

São calculadas as médias espectrais dos quatro quadrantes e seu coeficiente de variação:

\[
CV_Q=\frac{\sigma(q_1,q_2,q_3,q_4)}{\mu(q_1,q_2,q_3,q_4)+\varepsilon}.
\]

---

## 15. Triagem espectral de mídia sintética

O módulo `synthetic_spectral` produz flags de engenharia quando:

- número de picos radiais \(\ge4\);
- \(R_{HL}<0.30\) ou \(R_{HL}>1.25\);
- \(CV_Q<0.01\), interpretado como simetria espectral muito alta.

Esses limiares **não são probabilidades** nem regras universais de geração por IA.

---

# PARTE V — ANÁLISE FACIAL

## 16. Detecção de face

O pipeline usa o cascade Haar frontal do OpenCV para localizar regiões faciais. O detector é usado apenas para definir regiões de interesse; a presença/ausência de uma face não é evidência de deepfake.

---

## 17. Artefatos na região facial

Para cada face:

### 17.1 Variância do Laplaciano

\[
S=\operatorname{Var}(\nabla^2 I_{face}).
\]

É usada como medida simples de nitidez/textura.

### 17.2 Assimetria de luminância esquerda-direita

\[
A_L=\frac{|\mu_{esq}-\mu_{dir}|}{255}.
\]

### 17.3 Relação entre densidade de bordas na fronteira e no interior

Bordas são obtidas por Canny. Define-se:

\[
R_E=\frac{\rho_{borda}}{\rho_{interior}+\varepsilon}.
\]

### Flags atuais

`face_boundary_texture_discontinuity` quando:

\[
R_E\ge1.15 \quad\text{e}\quad S<700.
\]

`face_luminance_texture_inconsistency` quando:

\[
A_L\ge0.12 \quad\text{e}\quad S<700.
\]

### Limitação

Iluminação, maquiagem, profundidade de campo, compressão e processamento de câmera podem produzir sinais semelhantes.

---

## 18. Consistência face versus contexto

Para cada face, o MFLab constrói uma vizinhança ao redor e exclui os pixels da própria face.

### Razão de ruído

\[
R_N=\frac{\sigma(R_{face})}{\sigma(R_{contexto})+\varepsilon}.
\]

Flag quando:

\[
R_N<0.45 \quad\text{ou}\quad R_N>2.2.
\]

### Razão de nitidez

\[
R_S=\frac{\operatorname{Var}(\nabla^2 I_{face})}{\operatorname{Var}(\nabla^2 I_{contexto})+\varepsilon}.
\]

Flag quando:

\[
R_S<0.35 \quad\text{ou}\quad R_S>2.8.
\]

É um detector de inconsistência, não um classificador validado de face swap.

---

# PARTE VI — AUTOGAN E MÍDIA SINTÉTICA

## 19. AutoGAN-compatible spectral analysis

O módulo `autogan_spectral` é uma reprodução independente da ideia de análise espectral do AutoGAN, voltada a artefatos de upsampling em GANs.

### 19.1 Geometria de entrada

A imagem RGB é redimensionada para \(256\times256\) e recortada no centro para \(224\times224\).

### 19.2 FFT por canal

Para cada canal RGB \(x_c\):

\[
F_c=\mathcal F\{x_c\}.
\]

Usa-se:

\[
L_c=\log(|F_c|+10^{-3}).
\]

### 19.3 Normalização robusta P5/P95

Sejam \(P_5\) e \(P_{95}\) os percentis 5 e 95 de \(L_c\). O valor normalizado é:

\[
N_c=\operatorname{clip}\left(2\frac{L_c-P_5}{P_{95}-P_5}-1,-1,1\right).
\]

### 19.4 Bandas espectrais

No plano centralizado de \(224\times224\):

- `low`: região central `[57:177,57:177]`;
- `mid`: região `[21:203,21:203]` menos a região low;
- `high`: exterior da região `[21:203,21:203]`;
- `full`: espectro inteiro.

### 19.5 Descritores calculados

Para cada banda:

- média de \(|N|\);
- desvio padrão;
- fração de energia relativa para low/mid/high.

Também são calculados:

#### Autocorrelação de perfil espectral

Para perfil \(p\) centralizado:

\[
r(\ell)=\frac{\sum_i p_i p_{i+\ell}}{\sum_i p_i^2}.
\]

O maior pico em uma janela de lags é registrado separadamente nos eixos X e Y, junto com o lag correspondente.

#### Replicação entre quadrantes

São calculadas correlações de Pearson em módulo entre pares de quadrantes e tomada a média:

\[
R_Q=\operatorname{mean}_{a<b}|\rho(Q_a,Q_b)|.
\]

#### Estatísticas por canal

Para cada canal: média, desvio padrão e percentil 95 do módulo.

### 19.6 Papel atual na decisão automática

Este ponto é fundamental:

1. **`autogan_spectral` por si só é descritivo.** Atualmente retorna `screening_flags: []`. Portanto, executar o módulo não cria diretamente uma observação de suspeita nem uma família independente na fusão.
2. As features AutoGAN entram em `synthetic_handcrafted_v2`; logo, **podem influenciar indiretamente um classificador ML handcrafted configurado e treinado com essas features**.
3. O adaptador `autogan_classifier` pode produzir um voto de modelo quando um checkpoint é explicitamente configurado.
4. Na fusão, `autogan_classifier` só conta como família independente quando `validated=true`.
5. A conclusão automática do protocolo continua `inconclusive`.

Portanto, **o AutoGAN não está sendo usado como regra automática “GAN = verdadeiro/falso”**.

---

## 20. Classificador AutoGAN/ResNet34 opcional

Quando `MFLAB_AUTOGAN_CHECKPOINT` é configurado, o MFLab cria uma ResNet34 com duas saídas e carrega o checkpoint.

A convenção usada é:

```text
classe 0 = synthetic
classe 1 = real
```

Se os logits são \(z_0,z_1\), aplica-se softmax:

\[
p_i=\frac{e^{z_i}}{e^{z_0}+e^{z_1}}.
\]

Então:

\[
score_{synthetic}=p_0,\qquad score_{real}=p_1.
\]

A predição é:

\[
\text{synthetic se }p_0\ge p_1.
\]

### Como interpretar `score_synthetic`

Um valor como:

```text
score_synthetic = 0.87
```

significa **saída softmax da classe sintética do checkpoint**, não “87% de probabilidade forense de ser IA”. Só pode ser chamado de probabilidade calibrada se houver evidência independente de calibração.

### `validated` e `calibrated`

Esses campos vêm do JSON de metadados associado ao checkpoint. O MFLab não os presume verdadeiros.

### Segurança e rastreabilidade

O SHA-256 do checkpoint é registrado. O carregamento prefere `weights_only=True` em versões modernas de PyTorch.

### Escopo

O método é especificamente relacionado a artefatos de geração GAN/upsampling. Um resultado negativo não exclui diffusion, transformers ou outros geradores.

---

## 21. Banco de características sintéticas `synthetic_handcrafted_v2`

O vetor junta várias famílias.

### 21.1 Haar-wavelet multiescala

Para cada bloco 2x2:

\[
LL=\frac{a+b+c+d}{2},
\]
\[
LH=\frac{a-b+c-d}{2},
\]
\[
HL=\frac{a+b-c-d}{2},
\]
\[
HH=\frac{a-b-c+d}{2}.
\]

Em até três níveis, registra-se energia média de cada subbanda:

\[
E_{LH}=\operatorname{mean}(LH^2),
\]

analogamente para HL e HH, além da soma de alta frequência.

### 21.2 Correlação RGB

Para pares de canais:

\[
\rho_{XY}=\frac{\operatorname{Cov}(X,Y)}{\sigma_X\sigma_Y}.
\]

São extraídas `RG`, `RB` e `GB`.

### 21.3 GLCM

A imagem é reduzida a \(256\times256\), quantizada em 16 níveis e são construídas matrizes de coocorrência para distâncias 1 e 2 e ângulos \(0,\pi/4,\pi/2\).

O MFLab calcula médias de:

- contraste;
- dissimilaridade;
- homogeneidade;
- energia;
- correlação.

Exemplo de contraste:

\[
Contrast=\sum_{i,j}(i-j)^2P(i,j).
\]

### 21.4 LBP uniforme

Usa Local Binary Pattern com \(P=8\), \(R=1\), método `uniform`. O histograma dos 10 bins uniformes é usado como característica.

### 21.5 HOG

Configuração:

- 9 orientações;
- célula \(16\times16\);
- bloco \(2\times2\) células;
- normalização L2-Hys.

O vetor HOG não é armazenado integralmente; são resumidos:

- média;
- desvio padrão;
- percentil 90;
- esparsidade \(P(HOG<10^{-3})\).

### 21.6 FFT multibanda radial

Quatro bandas radiais:

\[
[0.05,0.25),\ [0.25,0.50),\ [0.50,0.75),\ [0.75,1.0)
\]

em relação ao raio máximo. Registra-se a média por banda e:

\[
R_{HF/LF}=\frac{B_4}{B_1+\varepsilon}.
\]

### 21.7 Momentos de cor

Por canal RGB são usados:

\[
\mu,\qquad \sigma,
\]

\[
skew=\operatorname{mean}\left(\frac{X-\mu}{\sigma+\varepsilon}\right)^3.
\]

### 21.8 Features AutoGAN-compatible

Todos os descritores `autogan_*` da seção anterior são incorporados ao vetor final.

### Interpretação

O banco é **descritivo**. Ele só se torna classificador quando combinado com um modelo aprendido.

---

# PARTE VII — MODELOS APRENDIDOS

## 22. Classificador handcrafted opcional

Um bundle `joblib` deve conter:

- `feature_names`;
- `estimator`;
- `calibrated`;
- `validated`;
- metadados de validação.

O vetor é montado na ordem definida por `feature_names`.

Se o estimador possui `predict_proba`, usa-se a probabilidade da classe 1 como score. Se possui `decision_function`, usa-se a função de decisão. Caso contrário, usa-se a predição discreta.

### Interpretação

O score só é evidência dentro do domínio documentado. `validated=false` mantém o resultado como observação de triagem.

---

## 23. Detector profundo ONNX opcional

O adaptador espera entrada RGB `float32` no formato NCHW e intervalo \([0,1]\).

Se a saída do modelo possui um único logit \(z\):

\[
score=\sigma(z)=\frac{1}{1+e^{-z}}.
\]

Se há múltiplas saídas, aplica-se softmax e, na implementação atual, a última classe é tratada como score sintético:

\[
p_i=\frac{e^{z_i-z_{max}}}{\sum_j e^{z_j-z_{max}}}.
\]

### Limitação

O adaptador é genérico: a semântica das classes precisa corresponder ao checkpoint utilizado. O campo `validated` só é habilitado explicitamente por configuração.

---

# PARTE VIII — FUSÃO E DECISÃO DEEPFAKE

## 24. Fusão conservadora de famílias

`synthetic_evidence_fusion` não calcula probabilidade Bayesiana nem média ponderada de scores. Ele apenas conta famílias independentes que satisfazem critérios definidos.

Atualmente entram:

- `spectral`, se `synthetic_spectral` tiver flags;
- `face`, se houver flags faciais;
- `face_context`, se houver flags face-contexto;
- `noise`, se \(CV_{ruido}>0.75\);
- `sensor_residual`, se \(CV_{PRNU}>0.75\);
- `validated_provenance`, se C2PA estiver criptograficamente validado;
- `handcrafted_ml`, somente se o modelo estiver `validated=true`;
- `deep_model`, somente se estiver `validated=true`;
- `autogan_spectral_model`, somente se o classificador AutoGAN estiver `validated=true`.

A execução das features AutoGAN sem classificador validado **não conta como família independente**.

### Níveis

\[
N=\#\{\text{famílias independentes}\}.
\]

- \(N=0\): `no_convergent_signal`;
- \(N=1\): `single_family_observation`;
- \(2\le N<4\): `moderate_convergence_for_expert_review`;
- \(N\ge4\): `high_convergence_for_expert_review`.

Mesmo em `high_convergence_for_expert_review`:

```text
evidentiary_conclusion = inconclusive
```

---

## 25. Lógica do `MFLAB-DF-0.6`

O protocolo combina o núcleo anterior com as novas famílias.

### 25.1 Observações nativas

Podem entrar como `screening_observations`:

- flags espectrais;
- flags faciais;
- marcador C2PA sem interpretação conclusiva;
- \(CV_{ruido}>0.75\);
- flag de reamostragem;
- \(CV_{PRNU}>0.75\);
- face-contexto;
- saídas positivas de modelos ainda não validados;
- convergência entre famílias.

Há ainda uma regra controlada `synthetic_texture`:

\[
R_{HL}<0.55 \quad\text{e}\quad \sigma_{PRNU-like}<0.02.
\]

Ela é explicitamente uma regra de engenharia associada à fixture sintética de regressão e não um detector populacional.

### 25.2 Modelos aprendidos

Para `synthetic_ml`, `synthetic_deep` e `autogan_classifier`:

- se `validated=true`, a saída entra em `evidence_families`;
- se não validado, mas o modelo aponta sintético ou score \(\ge0.5\), entra apenas em `screening_observations`.

### 25.3 Estados de triagem

- existe alguma `evidence_family` → `needs_expert_review`;
- sem evidência validada, mas existem observações → `screening_observations_only`;
- nenhum sinal → `no_strong_screening_signals`.

### Nota semântica importante

No código atual, **qualquer saída de modelo marcado como validado é adicionada a `evidence_families`, inclusive quando o próprio modelo favorece a classe real**. Consequentemente, `needs_expert_review` significa “há saída de evidência/modelo validado a revisar”, e não necessariamente “o sistema votou sintético”. A direção do voto deve ser lida no `predicted_label` e no `score`.

### Conclusão automática

Independentemente dos sinais:

```text
evidentiary_conclusion = inconclusive
```

Esse comportamento é deliberado.

---

# PARTE IX — VÍDEO

## 26. Timing e gaps de frames

O `ffprobe` fornece timestamps `best_effort_timestamp_time`. Para diferenças consecutivas:

\[
\Delta t_i=t_{i+1}-t_i.
\]

Se \(m\) é a mediana dos \(\Delta t_i\), um gap é registrado quando:

\[
\Delta t_i>1.8m.
\]

Também é contado o número de I-frames.

---

## 27. Frames adjacentes quase duplicados

Cada frame é convertido para cinza \(64\times64\). Para frames consecutivos:

\[
MAD_i=\frac{1}{4096}\sum_{x,y}|F_i-F_{i-1}|.
\]

O código atual usa limiar absoluto:

\[
MAD_i\le0.05.
\]

Como os valores nessa rotina permanecem na escala aproximadamente 0–255, esse limiar é extremamente estrito e tende a identificar duplicação praticamente exata.

---

## 28. Transições abruptas

Os frames são normalizados para \([0,1]\), reduzidos para \(64\times64\) e calcula-se MAD entre frames.

Se:

\[
m=\operatorname{mediana}(MAD_i),
\]

\[
MAD_r=\operatorname{mediana}(|MAD_i-m|),
\]

então o limiar robusto é:

\[
T_r=m+8\cdot1.4826\cdot MAD_r.
\]

O limiar final é:

\[
T=\max(0.01,T_r).
\]

Transições com \(MAD_i\ge T\) são sinalizadas.

---

## 29. Descontinuidade de movimento por fluxo óptico

Usa-se Farnebäck entre frames em cinza \(128\times128\). Para cada transição, calcula-se a magnitude do vetor de fluxo:

\[
M(x,y)=\sqrt{u(x,y)^2+v(x,y)^2},
\]

seguida da média espacial \(\bar M_i\).

Define-se robust z-score:

\[
z_i=\frac{\bar M_i-m}{1.4826\,MAD+\varepsilon}.
\]

O limiar atual é:

\[
z_i\ge2.0.
\]

É uma triagem não específica; movimento rápido de câmera e cortes legítimos também podem produzir outliers.

---

## 30. Triagem deepfake temporal em vídeo

O módulo nativo amostra até 24 frames aproximadamente equidistantes.

Em cada frame:

- procura faces com Haar cascade;
- para a maior face calcula variância do Laplaciano e luminância média;
- redimensiona o frame cinza para \(256\times256\);
- aplica DCT;
- calcula energia média de baixa frequência no bloco `[:64,:64]`;
- calcula energia média de alta frequência no bloco `[128:,128:]`;
- forma a razão alta/baixa.

Para uma série de valores \(x_i\), usa-se:

\[
CV=\frac{\sigma(x)}{\mu(x)+\varepsilon}.
\]

Flags atuais:

- `face_sharpness_cv > 1.0`;
- `spectral_ratio_cv > 0.75`.

Não há inferência explícita de piscadas ou microexpressões.

---

# PARTE X — MÉTODOS COM REFERÊNCIA

## 31. Diferença de imagem com referência

Só é usada quando existe imagem de referência de mesma dimensão.

Calcula-se diferença média por pixel entre canais:

\[
D(x,y)=\operatorname{mean}_c |I_q-I_r|.
\]

Se:

\[
m=\operatorname{mediana}(D),\qquad MAD=\operatorname{mediana}(|D-m|),
\]

então:

\[
T=\max(12,\;m+8\cdot1.4826\cdot MAD).
\]

Cria-se máscara binária \(D\ge T\), seguida de abertura morfológica \(3\times3\) e fechamento \(7\times7\). Componentes conexos com área menor que 50 pixels são removidos.

### Interpretação

Localiza alteração relativa à referência; não determina se a alteração foi splice, inpainting, face swap ou outro tipo de edição.

---

## 32. Alinhamento de vídeo com referência

Os vídeos são convertidos em sequências de frames cinza \(64\times64\). É calculada matriz de custo:

\[
D_{ij}=\operatorname{mean}|Q_i-R_j|.
\]

O algoritmo escolhe, para cada frame questionado, o frame de referência de menor custo **respeitando ordem monotônica crescente**.

Se dois matches consecutivos saltam de \(j\) para \(j+k\), com \(k>1\), o intervalo intermediário é registrado como possível segmento ausente.

### Limitação

É comparação assistida por referência, não detecção cega de exclusão de frames.

---

# PARTE XI — ESTEGANOGRAFIA

## 33. Triagem LSB

Para cada canal RGB, extrai-se o bit menos significativo:

\[
b_i=I_i\ \&\ 1.
\]

Conta-se \(n_0\), \(n_1\) e:

\[
p_1=\frac{n_1}{n_0+n_1}.
\]

A entropia binária é:

\[
H=-p_1\log_2p_1-(1-p_1)\log_2(1-p_1).
\]

O teste qui-quadrado contra equilíbrio 50/50 é:

\[
\chi^2=\frac{(n_0-E)^2+(n_1-E)^2}{E},\qquad E=\frac{n_0+n_1}{2}.
\]

O p-valor é calculado com 1 grau de liberdade.

### Limitação

LSBs balanceados não provam esteganografia. Métodos modernos de embedding exigem esteganálise especializada.

---

# PARTE XII — COPY-MOVE

## 34. Copy-move por ORB

### 34.1 Pontos e descritores

O ORB detecta até 5000 keypoints. Os descritores binários são comparados por distância de Hamming:

\[
d_H(a,b)=\sum_i \mathbf1[a_i\ne b_i].
\]

### 34.2 Filtros de pares

Um par candidato precisa satisfazer:

\[
d_H\le55
\]

e distância espacial:

\[
\|p_2-p_1\|\ge40\text{ px}.
\]

### 34.3 Vetor de deslocamento

\[
\Delta p=p_2-p_1.
\]

Os deslocamentos são quantizados em bins de 8 px.

### 34.4 Cluster suspeito

Um cluster é marcado quando simultaneamente:

- pelo menos 10 matches;
- Hamming médio \(\le40\);
- norma do desvio padrão do deslocamento \(\le1.2\) px.

O score de apresentação é:

\[
score=\min\left(1,\frac{N_{pares\ suspeitos}}{20}\right).
\]

### Limitação

Texturas repetitivas e estruturas semelhantes na cena podem produzir falsos positivos.

---

# PARTE XIII — BENCHMARK CIENTÍFICO

## 35. Separação treino/validação/teste

O benchmark científico é separado do GT de CI.

- `train`: ajuste dos modelos;
- `validation`: seleção quando disponível;
- `test`: avaliação final intocada;
- `test_holdout`: disponível para protocolos adicionais.

Sem validation explícita, a seleção usa validação cruzada estratificada apenas no treino.

---

## 36. Modelos comparados

### 36.1 Regressão logística

Após padronização:

\[
P(y=1|x)=\sigma(w^Tx+b).
\]

Usa `class_weight="balanced"`.

### 36.2 SVM com kernel RBF

\[
K(x_i,x_j)=\exp(-\gamma\|x_i-x_j\|^2).
\]

Configuração atual: `C=2.0`, `gamma="scale"`, pesos de classe balanceados e geração de probabilidades habilitada.

### 36.3 ExtraTrees

Ensemble de 300 árvores extremamente randomizadas, com pesos de classe balanceados.

### 36.4 HistGradientBoosting

Boosting de árvores sobre histogramas, conforme implementação do scikit-learn.

---

## 37. Seleção de modelo

A métrica de seleção é balanced accuracy:

\[
BA=\frac{Sensitivity+Specificity}{2}.
\]

Se não há validation explícita, usa-se `StratifiedKFold`, com até 5 folds, limitado pela menor classe.

---

## 38. Calibração

Quando existem pelo menos 3 exemplos por classe no conjunto de ajuste, o modelo selecionado é calibrado por `CalibratedClassifierCV(method="sigmoid")`.

Isso aproxima uma transformação logística entre score bruto e frequência empírica, mas a validade da calibração continua limitada ao domínio do dataset.

---

## 39. Métricas

Com matriz de confusão:

```text
             predito real   predito sintético
real              TN               FP
sintético         FN               TP
```

### Accuracy

\[
Accuracy=\frac{TP+TN}{TP+TN+FP+FN}.
\]

### Sensibilidade / Recall

\[
Sensitivity=\frac{TP}{TP+FN}.
\]

### Especificidade

\[
Specificity=\frac{TN}{TN+FP}.
\]

### FPR

\[
FPR=\frac{FP}{FP+TN}.
\]

### Precision

\[
Precision=\frac{TP}{TP+FP}.
\]

### F1

\[
F1=2\frac{Precision\cdot Recall}{Precision+Recall}.
\]

Também são calculados ROC-AUC, PR-AUC e Brier Score quando existe score contínuo.

### Brier Score

\[
BS=\frac1N\sum_i(p_i-y_i)^2.
\]

Quanto menor, melhor a correspondência entre score probabilístico e resultado observado, desde que o score possa ser tratado como probabilidade.

---

## 40. Cross-generator

Com `--cross-generator`, o pipeline retém um gerador sintético por rodada, treina nos demais e testa no gerador retido mais imagens reais de teste.

A finalidade é medir se o classificador aprendeu sinais generalizáveis ou apenas fingerprints de geradores conhecidos.

---

## 41. Avaliação científica do checkpoint AutoGAN

Se o checkpoint estiver configurado, ele é avaliado **separadamente** no test set final. O benchmark calcula:

- métricas globais;
- desempenho por gerador;
- desempenho por transformação;
- `validated` e `calibrated` conforme metadados.

A predição binária do benchmark usa:

\[
\hat y=1\quad\text{se}\quad score_{synthetic}\ge0.5.
\]

Esse limiar é a fronteira natural do classificador binário softmax, não um limiar forense universal.

---

# PARTE XIV — ARTEFATOS VISUAIS

## 42. Camada visual

Os PNGs em `case/visuals/` são transformações derivadas para explicabilidade. Entre eles:

- ELA;
- residual de ruído;
- espectro FFT;
- histograma RGB;
- curva JPEG Ghost;
- autocorrelação de reamostragem;
- overlay copy-move;
- overlay face-contexto;
- perfil de features sintéticas;
- diferença com referência;
- AutoGAN full/low/mid/high;
- perfil AutoGAN;
- timelines de vídeo e frames-chave.

Essas imagens **não criam uma nova família de evidência**; apenas visualizam resultados já calculados.

---

# PARTE XV — INTEGRAÇÕES EXTERNAS

## 43. Modelos externos

O MFLab pode importar resultados externos por `case/external/deepfake_scores.json`. Só resultados com `validated=true` e score presente são tratados pelo protocolo como saída de detector validado.

Isso permite integrar frameworks como DeepfakeBench sem acoplar seus pesos e dependências ao núcleo do projeto.

---

## 44. Veritas / CodeRafay

A integração opcional `veritas_upstream_crosscheck` é tratada como implementação secundária de cross-check. O resultado não é silenciosamente fundido com os métodos nativos como se fosse verdade independente garantida.

---

# PARTE XVI — COMO LER UM RESULTADO DO AUTOGAN NO `report.json`

## 45. `autogan_spectral`

Exemplo conceitual:

```json
{
  "status": "success",
  "feature_family": "gan_upsampling_spectral_artifacts",
  "features": {
    "autogan_low_energy_fraction": 0.41,
    "autogan_mid_energy_fraction": 0.35,
    "autogan_high_energy_fraction": 0.24,
    "autogan_replication_autocorr_peak_x": 0.18,
    "autogan_quadrant_replication_score": 0.62
  },
  "screening_flags": [],
  "screening_only": true,
  "validated": false
}
```

### Interpretação correta

Os números caracterizam o espectro. **Não existe, no código atual, um limiar do tipo `quadrant_replication_score > X => GAN`.** Para interpretá-los quantitativamente, é necessário comparar distribuições de imagens reais e sintéticas em benchmark científico.

---

## 46. `autogan_classifier`

Exemplo:

```json
{
  "status": "success",
  "score_synthetic": 0.82,
  "score_real": 0.18,
  "predicted_label": "synthetic",
  "validated": false,
  "calibrated": false
}
```

Leitura:

- o checkpoint favoreceu a classe sintética;
- 0.82 é score softmax, não probabilidade forense calibrada;
- como `validated=false`, a saída é apenas observação de triagem;
- não deve ser generalizada para diffusion;
- o protocolo final continua inconclusivo.

Se o mesmo resultado tivesse `validated=true`, entraria como família de evidência de modelo e na contagem de convergência. Ainda assim, a conclusão automática permaneceria `inconclusive`.

---

# PARTE XVII — HIERARQUIA DE INTERPRETAÇÃO

## 47. Níveis conceituais

É útil separar:

### Nível A — integridade

“Este arquivo continua binariamente igual ao que foi hashado?”

Ferramenta principal: SHA-256.

### Nível B — proveniência

“Existe uma cadeia declarada/assinada de origem e processamento?”

Ferramentas: C2PA, metadados, contexto externo.

### Nível C — sinais forenses descritivos

“Existem padrões de compressão, ruído, frequência, textura, reamostragem ou inconsistência local?”

Ferramentas: ELA, JPEG, FFT, noise, PRNU-like, resampling, ORB, face-contexto, AutoGAN descriptors etc.

### Nível D — modelos aprendidos

“O classificador, no domínio para o qual foi treinado e validado, favorece determinada classe?”

Ferramentas: handcrafted ML, ONNX, AutoGAN/ResNet34, modelos externos.

### Nível E — convergência pericial

“Os métodos independentes, proveniência, contexto, arquivo de origem e modelos validados convergem para uma explicação tecnicamente sustentável?”

Essa última etapa não é reduzida, no MFLab, a uma regra automática binária.

---

# 48. Limitações gerais

1. **Ausência de sinal não prova autenticidade.**
2. **Presença de sinal não prova fraude.**
3. Recompressão, resize, screenshot, HDR, sharpening, denoising e redes sociais podem modificar várias famílias simultaneamente.
4. Detectores de IA sofrem com mudança de domínio e geradores não vistos.
5. GAN-specific detectors, como AutoGAN, não devem ser interpretados como detectores universais de diffusion.
6. O PRNU implementado é apenas residual PRNU-like, não identificação de câmera.
7. Métodos com referência dependem da confiabilidade e correspondência da referência.
8. O GT de CI em 100% mede regressão do software no dataset controlado, não sensibilidade/especificidade populacional.
9. Validação científica deve declarar datasets, splits, geradores, transformações, FPR, sensibilidade, calibração e hashes dos modelos.

---

# 49. Arquivos-fonte principais

```text
mf_lab/pipeline.py
mf_lab/analysis/image.py
mf_lab/analysis/classical.py
mf_lab/analysis/deepfake.py
mf_lab/analysis/deepfake_v2.py
mf_lab/analysis/face_context.py
mf_lab/analysis/autogan_spectral.py
mf_lab/analysis/synthetic_features.py
mf_lab/analysis/synthetic_ml.py
mf_lab/analysis/synthetic_deep.py
mf_lab/analysis/fusion.py
mf_lab/analysis/reference.py
mf_lab/analysis/video.py
mf_lab/analysis/c2pa.py
mf_lab/analysis/metadata.py
mf_lab/integrations/autogan.py
mf_lab/integrations/external.py
mf_lab/benchmark/synthetic.py
mf_lab/visual_artifacts.py
mf_lab/autogan_visuals.py
```

As referências bibliográficas usadas pelo registry de métodos são mantidas em:

```text
bibliography/references.yaml
```

---

# 50. Resumo operacional

O MFLab não é um único detector. É um **sistema de exame multimétodo**. A lógica desejada é:

\[
\text{integridade}
+\text{proveniência}
+\text{forense clássica}
+\text{mídia sintética}
+\text{modelos validados}
+\text{contexto}
\longrightarrow
\text{interpretação pericial}.
\]

No estado atual da v0.8, a política automática continua deliberadamente conservadora:

```text
triage != evidentiary verdict
score != calibrated probability
visual salience != proof
autogan_spectral != universal AI detector
evidentiary_conclusion = inconclusive
```
