# LAUDO TÉCNICO PERICIAL PRELIMINAR - case-2026-001

**Objeto:** Exame preliminar de autenticidade de mídia digital

## 1. Identificação e objeto da perícia
Examinar os arquivos digitais disponibilizados quanto a integridade, estrutura, indícios de processamento/manipulação, continuidade temporal e, quando aplicável, indícios de geração sintética. Este documento é preliminar e não substitui exame pericial completo nem avaliação de cadeia de custódia externa ao laboratório.

## 2. Material recebido
- img_001_pristine.jpg - SHA-256 `011901a3f9084e22497e2b27642b44a39e8965c4c2febc5ddf2c3ccf298c8787`
- img_002_copy_move.jpg - SHA-256 `afffbf1117c295e80758a534d0def6ce3eaed91e3dc57c20c12e5a84ba70fdaa`
- img_003_splice.jpg - SHA-256 `e34e12e63ef548eedee6696e46efd13a99f14e0e8cce12af0c4d5a8733816302`
- img_004_double_jpeg.jpg - SHA-256 `283ee8c3c09821fa6d554b41f0369a176c20b5a559bc0fb87e8186696d810154`
- img_005_resampled.jpg - SHA-256 `d782ab24f9e6e1263d95ec892ed366781207c1bc699bc3c0bdbc1fc2245cbd76`
- img_006_inpainted.jpg - SHA-256 `e90fb275c9ad8401c4656915620b120eea731974447fa337155b686ed67e6459`
- vid_001_pristine.mp4 - SHA-256 `a30ec9df06f581cd52243db14357dfee1e8e8aeec7778bf4b6f196e7ca5a383e`
- vid_002_duplicated_frames.mp4 - SHA-256 `0b56f94aedc4d5c19f315e05e618f9e472433e4e63f47dab2ff4d781db4ed08d`
- vid_003_deleted_segment.mp4 - SHA-256 `595f48e2b0cf785e5583c74f11edce68f3b32cc683dd9b2a5fb1bc30f8656753`
- vid_004_overlay_edit.mp4 - SHA-256 `99bce14c3037eceb0da5c73c7ca08c748706e0092d4ae116e6cc69a59a66025e`

## 3. Cadeia de custódia e preservação
Os originais devem permanecer preservados; o laboratório registra SHA-256, tamanho e horário de análise. A documentação interna não substitui os registros externos de coleta, recebimento, transferência, guarda e acesso.

## 4. Metodologia
O exame combina integridade/proveniência, metadados/estrutura, compressão, sinal/ruído, possíveis manipulações locais e protocolo de mídia sintética. Métodos de triagem não são conclusivos isoladamente.

## 5. Resultados e discussão
### img_001_pristine.jpg
SHA-256: `011901a3f9084e22497e2b27642b44a39e8965c4c2febc5ddf2c3ccf298c8787`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "011901a3f9084e22497e2b27642b44a39e8965c4c2febc5ddf2c3ccf298c8787"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "7f775fc744f8a040", "dhash": "dd8dbd0d9d3295a6", "phash": "c2924c5532bddfc0", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 1.866087555885315, "max_error": 32, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -2.944225798273692e-06, "std": 0.032629262655973434, "mad": 0.0051345136016607285}`

**Consistência local de ruído - triagem:** `{"residual_mean": -3.591344466258306e-06, "residual_std": 0.03802305832505226, "residual_mad": 0.006097130477428436, "block_size": 64, "blocks": 64, "local_std_mean": 0.032235680337180384, "local_std_cv": 0.6254482525564651, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 141.54742431640625, "std": 82.06250275241352, "entropy_bits": 7.3644041330493035, "zero_bins": 0, "clipped_black_fraction": 0.1015625, "clipped_white_fraction": 0.0060882568359375}, "G": {"mean": 105.79202270507812, "std": 76.50425810782293, "entropy_bits": 7.418857712834207, "zero_bins": 0, "clipped_black_fraction": 0.113739013671875, "clipped_white_fraction": 0.001583099365234375}, "B": {"mean": 96.45427703857422, "std": 77.54561001275414, "entropy_bits": 7.340556107550817, "zero_bins": 0, "clipped_black_fraction": 0.129913330078125, "clipped_white_fraction": 0.002765655517578125}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.798526763916016, 13.231539726257324, 12.551506042480469, 12.030174255371094, 11.642909049987793, 11.375588417053223, 11.195821762084961, 10.963058471679688, 10.758572578430176, 10.672471046447754, 10.478228569030762, 10.396236419677734, 10.206656455993652, 10.103614807128906, 9.970770835876465, 9.902792930603027, 9.806200981140137, 9.766287803649902, 9.616981506347656, 9.530219078063965, 9.40268611907959, 9.325788497924805, 9.310580253601074, 9.272066116333008, 9.20395278930664, 9.126322746276855, 8.996066093444824, 8.935957908630371, 8.923751831054688, 8.88651180267334, 8.797709465026855, 8.761500358581543, 8.712859153747559, 8.684629440307617, 8.60482406616211, 8.611368179321289, 8.539161682128906, 8.507137298583984, 8.465415000915527, 8.420207977294922, 8.413061141967773, 8.349013328552246, 8.313493728637695, 8.265351295471191, 8.21004581451416, 8.16682815551757`

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.938307377014482, 0.859213847996046, 0.7942454828069812, 0.7543085529271081, 0.726006864418875, 0.7012718192766196, 0.6781758995602429, 0.6612863388979648, 0.6526185696603279, 0.6459873679140702, 0.6446767473722984, 0.6420179099986052, 0.624097171294243, 0.59843635385527, 0.5735486015448195, 0.5585412655250305, 0.5488252660699371, 0.5324426346627653, 0.5083851502629018, 0.49110703010316764, 0.4907506743136566, 0.49950281592333684, 0.49870017870759253, 0.48027158995168207, 0.44320222039639345, 0.4084410077719086, 0.38319369210715426, 0.36737837157256614, 0.3524811545458779, 0.3387661685540834, 0.33525820586949834, 0.3444298446083996], "y_autocorrelation": [0.9147336229387965, 0.8456056709699523, 0.7743326194525886, 0.7188570657884468, 0.6869869444748316, 0.6561293533401311, 0.6379977005037186, 0.6088791436353497, 0.5740030997382206, 0.5499517200176273, 0.5243154490`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.03260371461510658, "local_energy_mean": 0.027447373257018626, "local_energy_cv": 0.6410482146710064, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [177, 66, 94, 94], "laplacian_variance": 962.8191528320312, "left_right_mean_luminance_asymmetry": 0.08638280119653112, "boundary_edge_density": 0.16629213094711304, "interior_edge_density": 0.16893424093723297}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.798526763916016, 13.231539726257324, 12.551506042480469, 12.030174255371094, 11.642909049987793, 11.375588417053223, 11.195821762084961, 10.963058471679688, 10.758572578430176, 10.672471046447754, 10.478228569030762, 10.396236419677734, 10.206656455993652, 10.103614807128906, 9.970770835876465, 9.902792930603027, 9.806200981140137, 9.766287803649902, 9.616981506347656, 9.530219078063965, 9.40268611907959, 9.325788497924805, 9.310580253601074, 9.272066116333008, 9.20395278930664, 9.126322746276855, 8.996066093444824, 8.935957908630371, 8.923751831054688, 8.88651180267334, 8.797709465026855, 8.761500358581543, 8.712859153747559, 8.684629440307617, 8.60482406616211, 8.611368179321289, 8.539161682128906, 8.507137298583984, 8.465415000915527, 8.420207977294922, 8.413061141967773, 8.349013328552246, 8.313493728637695, 8.265351295471191, 8.21004581451416, 8.1`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [2, 1, 1, 2, 2, 4, 5, 6, 1, 1, 1, 2, 3, 6, 6, 6, 1, 1, 2, 2, 4, 6, 7, 6, 1, 2, 2, 3, 5, 9, 8, 6, 2, 2, 4, 6, 7, 11, 10, 8, 2, 4, 6, 6, 8, 10, 11, 9, 5, 6, 8, 9, 10, 12, 12, 10, 7, 9, 10, 10, 11, 10, 10, 10], "1": [2, 2, 2, 5, 10, 10, 10, 10, 2, 2, 3, 7, 10, 10, 10, 10, 2, 3, 6, 10, 10, 10, 10, 10, 5, 7, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]}, "fingerprints": {"0": {"sum": 369, "mean": 5.765625, "min": 1, "max": 12, "first_16": [2, 1, 1, 2, 2, 4, 5, 6, 1, 1, 1, 2, 3, 6, 6, 6]}, "1": {"sum": 558, "mean": 8.71875, "min": 2, "max": 10, "first_16": [2, 2, 2, 5, 10, 10, 10, 10, 2, 2, 3, 7, 10, 10, 10, 10]}}, "warning": "Quantization tables can indicate encoding history/software families but are not unique identifiers of manipula`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 3.41802978515625, "local_cv": 0.5881353044620328}, {"quality": 60, "mean_abs_error": 3.276036500930786, "local_cv": 0.5813931535500636}, {"quality": 65, "mean_abs_error": 3.1012890338897705, "local_cv": 0.5762664993873933}, {"quality": 70, "mean_abs_error": 2.9917423725128174, "local_cv": 0.5276877866481137}, {"quality": 75, "mean_abs_error": 2.7197203636169434, "local_cv": 0.5606942272624311}, {"quality": 80, "mean_abs_error": 2.5008606910705566, "local_cv": 0.5574468033182259}, {"quality": 85, "mean_abs_error": 2.1522510051727295, "local_cv": 0.5336481002404875}, {"quality": 90, "mean_abs_error": 1.8660876750946045, "local_cv": 0.5370154582550953}, {"quality": 95, "mean_abs_error": 0.38439053297042847, "local_cv": 1.0498166908378175}, {"quality": 100, "mean_abs_error": 0.4182701110839844, "local_cv": 0.8785250601862766}], "minimum_er`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.023081606793671824, "n_blocks": 4096, "zero_bin_fraction": 0.006578947368421052, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2500, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 142724, "n1": 119420, "p1": 0.4555511474609375, "entropy_bits": 0.9942918010194437, "chi2": 2071.672119140625, "pvalue": 0.0}, "G": {"n0": 144956, "n1": 117188, "p1": 0.4470367431640625, "entropy_bits": 0.991890968935843, "chi2": 2941.367431640625, "pvalue": 0.0}, "B": {"n0": 147008, "n1": 115136, "p1": 0.439208984375, "entropy_bits": 0.9893104764339582, "chi2": 3875.0625, "pvalue": 0.0}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### img_002_copy_move.jpg
SHA-256: `afffbf1117c295e80758a534d0def6ce3eaed91e3dc57c20c12e5a84ba70fdaa`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "afffbf1117c295e80758a534d0def6ce3eaed91e3dc57c20c12e5a84ba70fdaa"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "7f775fc744fc0440", "dhash": "dd8dbd0d9d3c95a6", "phash": "d2a24cd661bbdd48", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 0.9958292841911316, "max_error": 31, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -3.104064944636775e-06, "std": 0.032670944929122925, "mad": 0.0046681188978254795}`

**Consistência local de ruído - triagem:** `{"residual_mean": -3.739412932191044e-06, "residual_std": 0.03798317909240723, "residual_mad": 0.005622886121273041, "block_size": 64, "blocks": 64, "local_std_mean": 0.03231161232179147, "local_std_cv": 0.6178619950470228, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 145.32829666137695, "std": 79.78946260613435, "entropy_bits": 7.406193824995068, "zero_bins": 0, "clipped_black_fraction": 0.08710861206054688, "clipped_white_fraction": 0.005352020263671875}, "G": {"mean": 109.93510818481445, "std": 75.71540397843432, "entropy_bits": 7.4744451410239785, "zero_bins": 0, "clipped_black_fraction": 0.09832382202148438, "clipped_white_fraction": 0.001224517822265625}, "B": {"mean": 100.65801239013672, "std": 77.10374666827317, "entropy_bits": 7.413129338044561, "zero_bins": 0, "clipped_black_fraction": 0.11388397216796875, "clipped_white_fraction": 0.002349853515625}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.691723823547363, 13.199738502502441, 12.459985733032227, 12.120914459228516, 11.695379257202148, 11.409061431884766, 11.20993709564209, 10.936564445495605, 10.720010757446289, 10.619868278503418, 10.422613143920898, 10.39429759979248, 10.2155122756958, 10.089363098144531, 9.958601951599121, 9.891183853149414, 9.810311317443848, 9.72840404510498, 9.598584175109863, 9.534554481506348, 9.38703441619873, 9.322279930114746, 9.308531761169434, 9.260478019714355, 9.18028450012207, 9.125146865844727, 8.988024711608887, 8.913248062133789, 8.892693519592285, 8.837336540222168, 8.775445938110352, 8.739891052246094, 8.702519416809082, 8.662275314331055, 8.598875999450684, 8.5986909866333, 8.534704208374023, 8.50413990020752, 8.45980167388916, 8.394634246826172, 8.404407501220703, 8.351404190063477, 8.298952102661133, 8.26807689666748, 8.202025413513184, 8.167621612548828, 8.12`

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.9089472322387424, 0.7995498448853129, 0.7324014075043305, 0.6900803689507643, 0.6613798248525107, 0.6316823140712567, 0.6087696919892327, 0.5998746915529986, 0.5936271175275205, 0.5845345582751994, 0.5846555178802678, 0.5859960876496064, 0.5694585939354186, 0.5407494632887837, 0.5160984763261367, 0.50339949752736, 0.49253208975757273, 0.47408617094885114, 0.44711607647988916, 0.42471717627361383, 0.41994173193654827, 0.42198256586474253, 0.42103672434663, 0.40953595656040265, 0.37734678403575256, 0.33935105843282654, 0.30439664443225695, 0.2767280466331014, 0.25688330925598746, 0.24585973680197978, 0.2465452975774648, 0.26118526544039555], "y_autocorrelation": [0.7364887825556067, 0.5046261767749078, 0.45773832174972884, 0.4170169861669963, 0.39553295425229834, 0.3744273106495031, 0.37243132886503066, 0.3854546698495916, 0.3830781227805161, 0.3748676689775156, 0.`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.03264093026518822, "local_energy_mean": 0.027543820986466017, "local_energy_cv": 0.6358302969429934, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [178, 67, 92, 92], "laplacian_variance": 974.6865844726562, "left_right_mean_luminance_asymmetry": 0.090818784980911, "boundary_edge_density": 0.16494253277778625, "interior_edge_density": 0.17028553783893585}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.691723823547363, 13.199738502502441, 12.459985733032227, 12.120914459228516, 11.695379257202148, 11.409061431884766, 11.20993709564209, 10.936564445495605, 10.720010757446289, 10.619868278503418, 10.422613143920898, 10.39429759979248, 10.2155122756958, 10.089363098144531, 9.958601951599121, 9.891183853149414, 9.810311317443848, 9.72840404510498, 9.598584175109863, 9.534554481506348, 9.38703441619873, 9.322279930114746, 9.308531761169434, 9.260478019714355, 9.18028450012207, 9.125146865844727, 8.988024711608887, 8.913248062133789, 8.892693519592285, 8.837336540222168, 8.775445938110352, 8.739891052246094, 8.702519416809082, 8.662275314331055, 8.598875999450684, 8.5986909866333, 8.534704208374023, 8.50413990020752, 8.45980167388916, 8.394634246826172, 8.404407501220703, 8.351404190063477, 8.298952102661133, 8.26807689666748, 8.202025413513184, 8.16762161`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [3, 2, 2, 3, 4, 6, 8, 10, 2, 2, 2, 3, 4, 9, 10, 9, 2, 2, 3, 4, 6, 9, 11, 9, 2, 3, 4, 5, 8, 14, 13, 10, 3, 4, 6, 9, 11, 17, 16, 12, 4, 6, 9, 10, 13, 17, 18, 15, 8, 10, 12, 14, 16, 19, 19, 16, 12, 15, 15, 16, 18, 16, 16, 16], "1": [3, 3, 4, 8, 16, 16, 16, 16, 3, 3, 4, 11, 16, 16, 16, 16, 4, 4, 9, 16, 16, 16, 16, 16, 8, 11, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16]}, "fingerprints": {"0": {"sum": 592, "mean": 9.25, "min": 2, "max": 19, "first_16": [3, 2, 2, 3, 4, 6, 8, 10, 2, 2, 2, 3, 4, 9, 10, 9]}, "1": {"sum": 891, "mean": 13.921875, "min": 3, "max": 16, "first_16": [3, 3, 4, 8, 16, 16, 16, 16, 3, 3, 4, 11, 16, 16, 16, 16]}}, "warning": "Quantization tables can indicate encoding history/software families but are not unique iden`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 3.3953804969787598, "local_cv": 0.5842624381336899}, {"quality": 60, "mean_abs_error": 3.2261757850646973, "local_cv": 0.579073626823151}, {"quality": 65, "mean_abs_error": 3.064753293991089, "local_cv": 0.579165567835053}, {"quality": 70, "mean_abs_error": 2.9313366413116455, "local_cv": 0.5419323111904444}, {"quality": 75, "mean_abs_error": 2.6047630310058594, "local_cv": 0.5681562776797595}, {"quality": 80, "mean_abs_error": 2.3995423316955566, "local_cv": 0.5594721793345973}, {"quality": 85, "mean_abs_error": 2.081273317337036, "local_cv": 0.5885029949661201}, {"quality": 90, "mean_abs_error": 0.9958292841911316, "local_cv": 0.6640763074275544}, {"quality": 95, "mean_abs_error": 0.7799173593521118, "local_cv": 0.6429088866478526}, {"quality": 100, "mean_abs_error": 0.4108530879020691, "local_cv": 0.9133846450891994}], "minimum_erro`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.12136177647114078, "n_blocks": 4096, "zero_bin_fraction": 0.08496732026143791, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2498, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 140407, "n1": 121737, "p1": 0.4643898010253906, "entropy_bits": 0.9963379769372451, "chi2": 1329.684829711914, "pvalue": 4.002649800871539e-291}, "G": {"n0": 142461, "n1": 119683, "p1": 0.4565544128417969, "entropy_bits": 0.9945468972512627, "chi2": 1979.2071685791016, "pvalue": 0.0}, "B": {"n0": 145076, "n1": 117068, "p1": 0.4465789794921875, "entropy_bits": 0.9917499199976034, "chi2": 2992.431884765625, "pvalue": 0.0}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### img_003_splice.jpg
SHA-256: `e34e12e63ef548eedee6696e46efd13a99f14e0e8cce12af0c4d5a8733816302`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "e34e12e63ef548eedee6696e46efd13a99f14e0e8cce12af0c4d5a8733816302"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "7f775fc764f80040", "dhash": "dd8dbd0dcdd295a6", "phash": "c2924cc532bdddc8", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 0.2836367189884186, "max_error": 29, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -3.1343442969955504e-06, "std": 0.03175648674368858, "mad": 0.004078269004821777}`

**Consistência local de ruído - triagem:** `{"residual_mean": -3.800783360929927e-06, "residual_std": 0.0370684452354908, "residual_mad": 0.004955589771270752, "block_size": 64, "blocks": 64, "local_std_mean": 0.03126783005063771, "local_std_cv": 0.6366803860994622, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 141.2209930419922, "std": 81.99223149952786, "entropy_bits": 7.4135273978624285, "zero_bins": 0, "clipped_black_fraction": 0.10004806518554688, "clipped_white_fraction": 0.00670623779296875}, "G": {"mean": 107.89953231811523, "std": 78.30803741338534, "entropy_bits": 7.440124791007466, "zero_bins": 0, "clipped_black_fraction": 0.11314773559570312, "clipped_white_fraction": 0.00174713134765625}, "B": {"mean": 96.14401626586914, "std": 79.0752729257152, "entropy_bits": 7.3252144542400925, "zero_bins": 0, "clipped_black_fraction": 0.13216781616210938, "clipped_white_fraction": 0.002872467041015625}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.854032516479492, 13.228899955749512, 12.580557823181152, 12.164424896240234, 11.741623878479004, 11.441015243530273, 11.22091007232666, 10.982462882995605, 10.761507034301758, 10.652527809143066, 10.513707160949707, 10.397863388061523, 10.213105201721191, 10.105714797973633, 9.929228782653809, 9.876361846923828, 9.79711627960205, 9.754193305969238, 9.576781272888184, 9.491950988769531, 9.382452011108398, 9.287525177001953, 9.271090507507324, 9.223417282104492, 9.187844276428223, 9.0536470413208, 8.967403411865234, 8.890176773071289, 8.896905899047852, 8.838666915893555, 8.730269432067871, 8.716291427612305, 8.692745208740234, 8.633340835571289, 8.55785083770752, 8.533665657043457, 8.50638484954834, 8.45536994934082, 8.403928756713867, 8.365204811096191, 8.364428520202637, 8.32513427734375, 8.250346183776855, 8.207498550415039, 8.16672420501709, 8.094783782958984, 8`

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.8383107436621379, 0.6717936524428264, 0.6256425320345209, 0.6012685965260284, 0.5979558258100752, 0.5838814194291411, 0.5631631174318147, 0.5489746337520705, 0.5222218432719, 0.5084167850892128, 0.5070592854356422, 0.5039954728016149, 0.5039374866952708, 0.4879935636862413, 0.46883056196727546, 0.46555594393166455, 0.4488980626006075, 0.4300391844753145, 0.4052203116941058, 0.3836284518370114, 0.3903218980307086, 0.39985801554367884, 0.39848871219021964, 0.3928281387640865, 0.3554734359880013, 0.3245008567065296, 0.3073759961835141, 0.2966349580434907, 0.2832725548036742, 0.263169767845107, 0.26021575032357225, 0.27064063868907856], "y_autocorrelation": [0.737536163703562, 0.4961475342039752, 0.44302650827886497, 0.3874670920671411, 0.3520973620531522, 0.32565001655099995, 0.3109061914058035, 0.3025185760150925, 0.29502794035885493, 0.27537605651545516, 0.2412356`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.03174982964992523, "local_energy_mean": 0.026553525578492554, "local_energy_cv": 0.6554561177958471, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [177, 66, 95, 95], "laplacian_variance": 943.2615966796875, "left_right_mean_luminance_asymmetry": 0.08909861742382656, "boundary_edge_density": 0.17222222685813904, "interior_edge_density": 0.17024222016334534}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.854032516479492, 13.228899955749512, 12.580557823181152, 12.164424896240234, 11.741623878479004, 11.441015243530273, 11.22091007232666, 10.982462882995605, 10.761507034301758, 10.652527809143066, 10.513707160949707, 10.397863388061523, 10.213105201721191, 10.105714797973633, 9.929228782653809, 9.876361846923828, 9.79711627960205, 9.754193305969238, 9.576781272888184, 9.491950988769531, 9.382452011108398, 9.287525177001953, 9.271090507507324, 9.223417282104492, 9.187844276428223, 9.0536470413208, 8.967403411865234, 8.890176773071289, 8.896905899047852, 8.838666915893555, 8.730269432067871, 8.716291427612305, 8.692745208740234, 8.633340835571289, 8.55785083770752, 8.533665657043457, 8.50638484954834, 8.45536994934082, 8.403928756713867, 8.365204811096191, 8.364428520202637, 8.32513427734375, 8.250346183776855, 8.207498550415039, 8.16672420501709, 8.09478`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [3, 2, 2, 3, 5, 8, 10, 12, 2, 2, 3, 4, 5, 12, 12, 11, 3, 3, 3, 5, 8, 11, 14, 11, 3, 3, 4, 6, 10, 17, 16, 12, 4, 4, 7, 11, 14, 22, 21, 15, 5, 7, 11, 13, 16, 21, 23, 18, 10, 13, 16, 17, 21, 24, 24, 20, 14, 18, 19, 20, 22, 20, 21, 20], "1": [3, 4, 5, 9, 20, 20, 20, 20, 4, 4, 5, 13, 20, 20, 20, 20, 5, 5, 11, 20, 20, 20, 20, 20, 9, 13, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20]}, "fingerprints": {"0": {"sum": 736, "mean": 11.5, "min": 2, "max": 24, "first_16": [3, 2, 2, 3, 5, 8, 10, 12, 2, 2, 3, 4, 5, 12, 12, 11]}, "1": {"sum": 1110, "mean": 17.34375, "min": 3, "max": 20, "first_16": [3, 4, 5, 9, 20, 20, 20, 20, 4, 4, 5, 13, 20, 20, 20, 20]}}, "warning": "Quantization tables can indicate encoding history/software families but are no`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 3.2382736206054688, "local_cv": 0.5883360047714847}, {"quality": 60, "mean_abs_error": 3.1124229431152344, "local_cv": 0.5921018524592838}, {"quality": 65, "mean_abs_error": 2.895185947418213, "local_cv": 0.5913940611877776}, {"quality": 70, "mean_abs_error": 2.7300477027893066, "local_cv": 0.5388227840326468}, {"quality": 75, "mean_abs_error": 2.5115737915039062, "local_cv": 0.5852019014125098}, {"quality": 80, "mean_abs_error": 2.3607444763183594, "local_cv": 0.6046232528311731}, {"quality": 85, "mean_abs_error": 1.5609372854232788, "local_cv": 0.6309106581437125}, {"quality": 90, "mean_abs_error": 0.28363674879074097, "local_cv": 1.243900096734804}, {"quality": 95, "mean_abs_error": 0.5993919372558594, "local_cv": 0.7518336092102932}, {"quality": 100, "mean_abs_error": 0.40642550587654114, "local_cv": 0.9094838773503517}], "minimum_`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.16607163691244842, "n_blocks": 4096, "zero_bin_fraction": 0.15894039735099338, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2500, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 142022, "n1": 120122, "p1": 0.45822906494140625, "entropy_bits": 0.9949596670695908, "chi2": 1829.5669555664062, "pvalue": 0.0}, "G": {"n0": 144255, "n1": 117889, "p1": 0.4497108459472656, "entropy_bits": 0.9926904982821481, "chi2": 2651.847671508789, "pvalue": 0.0}, "B": {"n0": 147479, "n1": 114665, "p1": 0.4374122619628906, "entropy_bits": 0.9886675745368902, "chi2": 4107.508071899414, "pvalue": 0.0}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### img_004_double_jpeg.jpg
SHA-256: `283ee8c3c09821fa6d554b41f0369a176c20b5a559bc0fb87e8186696d810154`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "283ee8c3c09821fa6d554b41f0369a176c20b5a559bc0fb87e8186696d810154"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "7f775fc744f8a060", "dhash": "dd8dbd0d9d3295a6", "phash": "c2924c5532bddfc0", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 0.47164154052734375, "max_error": 12, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -3.5694406506081577e-06, "std": 0.03252936527132988, "mad": 0.004007428884506226}`

**Consistência local de ruído - triagem:** `{"residual_mean": -4.090430138603551e-06, "residual_std": 0.03786329925060272, "residual_mad": 0.0049701351672410965, "block_size": 64, "blocks": 64, "local_std_mean": 0.03171179885248421, "local_std_cv": 0.6522827828904234, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 141.61820602416992, "std": 81.85182165053891, "entropy_bits": 7.401498966543265, "zero_bins": 0, "clipped_black_fraction": 0.0107879638671875, "clipped_white_fraction": 0.0067901611328125}, "G": {"mean": 105.89064025878906, "std": 76.19208087558759, "entropy_bits": 7.463340144314062, "zero_bins": 0, "clipped_black_fraction": 0.02332305908203125, "clipped_white_fraction": 0.001201629638671875}, "B": {"mean": 96.72771072387695, "std": 77.10358999243007, "entropy_bits": 7.430761810393377, "zero_bins": 0, "clipped_black_fraction": 0.03821563720703125, "clipped_white_fraction": 0.00214385986328125}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.79419994354248, 13.229484558105469, 12.546747207641602, 12.027464866638184, 11.63928508758545, 11.37043285369873, 11.190421104431152, 10.958405494689941, 10.75421142578125, 10.666457176208496, 10.469326972961426, 10.387988090515137, 10.201475143432617, 10.092605590820312, 9.965934753417969, 9.899566650390625, 9.795964241027832, 9.75806999206543, 9.608041763305664, 9.52374267578125, 9.398130416870117, 9.319927215576172, 9.298971176147461, 9.262514114379883, 9.19484806060791, 9.121244430541992, 8.990647315979004, 8.93694019317627, 8.915236473083496, 8.862459182739258, 8.785027503967285, 8.76136302947998, 8.717154502868652, 8.689464569091797, 8.587519645690918, 8.598240852355957, 8.549924850463867, 8.495993614196777, 8.455598831176758, 8.41779899597168, 8.408231735229492, 8.346846580505371, 8.298440933227539, 8.278674125671387, 8.233203887939453, 8.179177284240723, 8.`

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.9197423669550161, 0.848814529778508, 0.8025970788160025, 0.7555308871216095, 0.7307342486149729, 0.6971628079147686, 0.6834918058857969, 0.6909969577946882, 0.6581827965962201, 0.6393957799748972, 0.6371437380425006, 0.6232789274989071, 0.6116759239014962, 0.5817967003510569, 0.5676387613564213, 0.5704386309211863, 0.5336716052810254, 0.5111563764531003, 0.4946030768336721, 0.4708275833685424, 0.4761219810095625, 0.4723469293628254, 0.4755448651962447, 0.48038635511514954, 0.427915607595119, 0.3906463549372375, 0.36925355280596855, 0.3402586262631602, 0.32942395282026177, 0.30981853658262964, 0.3160426273539311, 0.3423488961902043], "y_autocorrelation": [0.9001336207434942, 0.8165452669054247, 0.7653485047345504, 0.7211615911072876, 0.6894326581746727, 0.6542616933839449, 0.6654753137162011, 0.6720912126134232, 0.6078328294467584, 0.5564251352236949, 0.5319904705`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.0324142687022686, "local_energy_mean": 0.026843614352401346, "local_energy_cv": 0.6767780688374153, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [177, 67, 93, 93], "laplacian_variance": 778.7691040039062, "left_right_mean_luminance_asymmetry": 0.07801945044676575, "boundary_edge_density": 0.1607954502105713, "interior_edge_density": 0.16852954030036926}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.79419994354248, 13.229484558105469, 12.546747207641602, 12.027464866638184, 11.63928508758545, 11.37043285369873, 11.190421104431152, 10.958405494689941, 10.75421142578125, 10.666457176208496, 10.469326972961426, 10.387988090515137, 10.201475143432617, 10.092605590820312, 9.965934753417969, 9.899566650390625, 9.795964241027832, 9.75806999206543, 9.608041763305664, 9.52374267578125, 9.398130416870117, 9.319927215576172, 9.298971176147461, 9.262514114379883, 9.19484806060791, 9.121244430541992, 8.990647315979004, 8.93694019317627, 8.915236473083496, 8.862459182739258, 8.785027503967285, 8.76136302947998, 8.717154502868652, 8.689464569091797, 8.587519645690918, 8.598240852355957, 8.549924850463867, 8.495993614196777, 8.455598831176758, 8.41779899597168, 8.408231735229492, 8.346846580505371, 8.298440933227539, 8.278674125671387, 8.233203887939453, 8.179177`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [3, 2, 2, 3, 4, 6, 8, 10, 2, 2, 2, 3, 4, 9, 10, 9, 2, 2, 3, 4, 6, 9, 11, 9, 2, 3, 4, 5, 8, 14, 13, 10, 3, 4, 6, 9, 11, 17, 16, 12, 4, 6, 9, 10, 13, 17, 18, 15, 8, 10, 12, 14, 16, 19, 19, 16, 12, 15, 15, 16, 18, 16, 16, 16], "1": [3, 3, 4, 8, 16, 16, 16, 16, 3, 3, 4, 11, 16, 16, 16, 16, 4, 4, 9, 16, 16, 16, 16, 16, 8, 11, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16]}, "fingerprints": {"0": {"sum": 592, "mean": 9.25, "min": 2, "max": 19, "first_16": [3, 2, 2, 3, 4, 6, 8, 10, 2, 2, 2, 3, 4, 9, 10, 9]}, "1": {"sum": 891, "mean": 13.921875, "min": 3, "max": 16, "first_16": [3, 3, 4, 8, 16, 16, 16, 16, 3, 3, 4, 11, 16, 16, 16, 16]}}, "warning": "Quantization tables can indicate encoding history/software families but are not unique iden`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 2.4027225971221924, "local_cv": 0.5120037452396663}, {"quality": 60, "mean_abs_error": 1.9111875295639038, "local_cv": 0.5456079226224343}, {"quality": 65, "mean_abs_error": 1.4604198932647705, "local_cv": 0.41039686318784746}, {"quality": 70, "mean_abs_error": 0.6595611572265625, "local_cv": 0.7495177409363646}, {"quality": 75, "mean_abs_error": 1.0621922016143799, "local_cv": 0.5714920425306108}, {"quality": 80, "mean_abs_error": 1.077836275100708, "local_cv": 0.6317361632260475}, {"quality": 85, "mean_abs_error": 0.7051734924316406, "local_cv": 0.6680017418095755}, {"quality": 90, "mean_abs_error": 0.47164154052734375, "local_cv": 0.8000551761863345}, {"quality": 95, "mean_abs_error": 0.3915964961051941, "local_cv": 0.8086910394013983}, {"quality": 100, "mean_abs_error": 0.29680508375167847, "local_cv": 0.9080739600678738}], "minimu`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.19835922017589686, "n_blocks": 4096, "zero_bin_fraction": 0.2185430463576159, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2493, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 119691, "n1": 142453, "p1": 0.5434150695800781, "entropy_bits": 0.9945545650995905, "chi2": 1976.4276275634766, "pvalue": 0.0}, "G": {"n0": 121584, "n1": 140560, "p1": 0.53619384765625, "entropy_bits": 0.996216846560521, "chi2": 1373.62890625, "pvalue": 1.1296988190390802e-300}, "B": {"n0": 123335, "n1": 138809, "p1": 0.5295143127441406, "entropy_bits": 0.9974850904449114, "chi2": 913.4089508056641, "pvalue": 1.1937124702702874e-200}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### img_005_resampled.jpg
SHA-256: `d782ab24f9e6e1263d95ec892ed366781207c1bc699bc3c0bdbc1fc2245cbd76`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "d782ab24f9e6e1263d95ec892ed366781207c1bc699bc3c0bdbc1fc2245cbd76"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "fd7d5f4744f8a060", "dhash": "89adad9d9cb211b5", "phash": "d2b2cc4f73bb8150", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 1.3478431701660156, "max_error": 32, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -1.0147154171136208e-05, "std": 0.02390032447874546, "mad": 0.003954827785491943}`

**Consistência local de ruído - triagem:** `{"residual_mean": -1.2631608115043491e-05, "residual_std": 0.028966300189495087, "residual_mad": 0.004879891872406006, "block_size": 64, "blocks": 64, "local_std_mean": 0.02471259991216357, "local_std_cv": 0.6113176066108279, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 145.2617530822754, "std": 81.30451601932792, "entropy_bits": 7.368536884377874, "zero_bins": 0, "clipped_black_fraction": 0.0934295654296875, "clipped_white_fraction": 0.0048675537109375}, "G": {"mean": 107.852294921875, "std": 75.31754799185126, "entropy_bits": 7.474029315647747, "zero_bins": 0, "clipped_black_fraction": 0.10132217407226562, "clipped_white_fraction": 0.0013885498046875}, "B": {"mean": 96.81085968017578, "std": 77.05862573058762, "entropy_bits": 7.397548247700249, "zero_bins": 0, "clipped_black_fraction": 0.11849212646484375, "clipped_white_fraction": 0.00229644775390625}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.700443267822266, 13.196125984191895, 12.5383882522583, 12.031804084777832, 11.691462516784668, 11.344085693359375, 11.1017427444458, 10.908828735351562, 10.773458480834961, 10.584493637084961, 10.394885063171387, 10.249045372009277, 10.128589630126953, 9.982562065124512, 9.904942512512207, 9.818864822387695, 9.721320152282715, 9.597555160522461, 9.492453575134277, 9.309860229492188, 9.303722381591797, 9.279757499694824, 9.21296501159668, 9.110361099243164, 8.95547866821289, 8.893558502197266, 8.858719825744629, 8.794173240661621, 8.699479103088379, 8.616682052612305, 8.599162101745605, 8.546065330505371, 8.464215278625488, 8.403708457946777, 8.352874755859375, 8.280130386352539, 8.203689575195312, 8.194180488586426, 8.10666275024414, 8.038857460021973, 7.982405662536621, 7.912743091583252, 7.852046489715576, 7.784076690673828, 7.732707500457764, 7.683945655822754, `

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.9447912442939079, 0.9069272516701699, 0.8558960459037515, 0.8090514071536152, 0.7820248617607045, 0.759160230784374, 0.7488624313169719, 0.7458561584050085, 0.7334079178731985, 0.7222722584462098, 0.7053494210109893, 0.683175706681602, 0.657307878021185, 0.6311101409762933, 0.6163025804982862, 0.6079036272997398, 0.5996505066996267, 0.589495685318408, 0.5799093731487844, 0.5689826347265432, 0.5524824462249952, 0.5265110453229783, 0.5083677911843248, 0.48227834008076864, 0.4576694747487585, 0.440397467609283, 0.42702454215522095, 0.4172178285537906, 0.40153510578081963, 0.3766873716665776, 0.35651519649707536, 0.3325504213672447], "y_autocorrelation": [0.9158517723609615, 0.8592959638929885, 0.7839185437455354, 0.7298638825222952, 0.6869512213916149, 0.6413985124018086, 0.607283109867423, 0.5735511804088904, 0.5475274383607366, 0.5120703216503905, 0.49090098486791`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.02400144375860691, "local_energy_mean": 0.02034216399624711, "local_energy_cv": 0.6261025068427962, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [159, 50, 109, 109], "laplacian_variance": 351.7460632324219, "left_right_mean_luminance_asymmetry": 0.08213629973658752, "boundary_edge_density": 0.129045307636261, "interior_edge_density": 0.14496758580207825}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.700443267822266, 13.196125984191895, 12.5383882522583, 12.031804084777832, 11.691462516784668, 11.344085693359375, 11.1017427444458, 10.908828735351562, 10.773458480834961, 10.584493637084961, 10.394885063171387, 10.249045372009277, 10.128589630126953, 9.982562065124512, 9.904942512512207, 9.818864822387695, 9.721320152282715, 9.597555160522461, 9.492453575134277, 9.309860229492188, 9.303722381591797, 9.279757499694824, 9.21296501159668, 9.110361099243164, 8.95547866821289, 8.893558502197266, 8.858719825744629, 8.794173240661621, 8.699479103088379, 8.616682052612305, 8.599162101745605, 8.546065330505371, 8.464215278625488, 8.403708457946777, 8.352874755859375, 8.280130386352539, 8.203689575195312, 8.194180488586426, 8.10666275024414, 8.038857460021973, 7.982405662536621, 7.912743091583252, 7.852046489715576, 7.784076690673828, 7.732707500457764, 7.6839`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [2, 1, 1, 2, 3, 5, 6, 7, 1, 1, 2, 2, 3, 7, 7, 7, 2, 2, 2, 3, 5, 7, 8, 7, 2, 2, 3, 3, 6, 10, 10, 7, 2, 3, 4, 7, 8, 13, 12, 9, 3, 4, 7, 8, 10, 12, 14, 11, 6, 8, 9, 10, 12, 15, 14, 12, 9, 11, 11, 12, 13, 12, 12, 12], "1": [2, 2, 3, 6, 12, 12, 12, 12, 2, 3, 3, 8, 12, 12, 12, 12, 3, 3, 7, 12, 12, 12, 12, 12, 6, 8, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]}, "fingerprints": {"0": {"sum": 441, "mean": 6.890625, "min": 1, "max": 15, "first_16": [2, 1, 1, 2, 3, 5, 6, 7, 1, 1, 2, 2, 3, 7, 7, 7]}, "1": {"sum": 668, "mean": 10.4375, "min": 2, "max": 12, "first_16": [2, 2, 3, 6, 12, 12, 12, 12, 2, 3, 3, 8, 12, 12, 12, 12]}}, "warning": "Quantization tables can indicate encoding history/software families but are not unique identifiers of ma`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 2.8844501972198486, "local_cv": 0.5403071130502615}, {"quality": 60, "mean_abs_error": 2.7461676597595215, "local_cv": 0.537204707716456}, {"quality": 65, "mean_abs_error": 2.600055694580078, "local_cv": 0.5403753359961468}, {"quality": 70, "mean_abs_error": 2.4947116374969482, "local_cv": 0.48888541915357137}, {"quality": 75, "mean_abs_error": 2.274280548095703, "local_cv": 0.5405822651350776}, {"quality": 80, "mean_abs_error": 2.0221340656280518, "local_cv": 0.5436716855353976}, {"quality": 85, "mean_abs_error": 1.7855072021484375, "local_cv": 0.5396627605589474}, {"quality": 90, "mean_abs_error": 1.3478431701660156, "local_cv": 0.587365147846047}, {"quality": 95, "mean_abs_error": 0.4883715510368347, "local_cv": 0.685508444327074}, {"quality": 100, "mean_abs_error": 0.37797296047210693, "local_cv": 0.8869715812508902}], "minimum_err`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.1352999744490909, "n_blocks": 4096, "zero_bin_fraction": 0.10638297872340426, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2485, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 142243, "n1": 119901, "p1": 0.4573860168457031, "entropy_bits": 0.9947539094804929, "chi2": 1904.1632232666016, "pvalue": 0.0}, "G": {"n0": 143340, "n1": 118804, "p1": 0.4532012939453125, "entropy_bits": 0.9936713934487154, "chi2": 2296.506103515625, "pvalue": 0.0}, "B": {"n0": 146130, "n1": 116014, "p1": 0.44255828857421875, "entropy_bits": 0.9904584569752998, "chi2": 3459.8291625976562, "pvalue": 0.0}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### img_006_inpainted.jpg
SHA-256: `e90fb275c9ad8401c4656915620b120eea731974447fa337155b686ed67e6459`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=needs_expert_review; famílias de evidência sinalizadas=2; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "e90fb275c9ad8401c4656915620b120eea731974447fa337155b686ed67e6459"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "image", "format": "JPEG", "mode": "RGB", "size": [512, 512], "exif": {}}`

**Hashes perceptuais (similaridade):** `{"ahash": "7f775fc744f8a040", "dhash": "dd8dbd0d8d3295a6", "phash": "c292cc5532bdddc0", "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}`

**Error Level Analysis (ELA) - triagem:** `{"mean_abs_error": 1.286012053489685, "max_error": 33, "quality": 90, "warning": "ELA is exploratory only and is not proof of manipulation."}`

**Residual de ruído - triagem:** `{"mean": -3.0330966183100827e-06, "std": 0.032074324786663055, "mad": 0.004592627286911011}`

**Consistência local de ruído - triagem:** `{"residual_mean": -3.6632172850659117e-06, "residual_std": 0.03736176714301109, "residual_mad": 0.00553131103515625, "block_size": 64, "blocks": 64, "local_std_mean": 0.03160290508822072, "local_std_cv": 0.6305079663649565, "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns."}`

**Histograma RGB - triagem:** `{"channels": {"R": {"mean": 141.33332061767578, "std": 82.17056513288638, "entropy_bits": 7.378722261233146, "zero_bins": 0, "clipped_black_fraction": 0.09941864013671875, "clipped_white_fraction": 0.0061798095703125}, "G": {"mean": 105.49602127075195, "std": 76.56817102348487, "entropy_bits": 7.429071007213301, "zero_bins": 0, "clipped_black_fraction": 0.11093521118164062, "clipped_white_fraction": 0.001689910888671875}, "B": {"mean": 96.18135833740234, "std": 77.57192972389878, "entropy_bits": 7.348723242622454, "zero_bins": 0, "clipped_black_fraction": 0.12796401977539062, "clipped_white_fraction": 0.002887725830078125}}, "warning": "Histogram anomalies are non-specific and require contextual interpretation.", "gray_dynamic_range": 255}`

**Análise em frequência FFT - triagem:** `{"radial_profile": [13.826834678649902, 13.219463348388672, 12.545708656311035, 12.019535064697266, 11.664786338806152, 11.379905700683594, 11.181005477905273, 10.960786819458008, 10.773842811584473, 10.648115158081055, 10.467577934265137, 10.388530731201172, 10.190893173217773, 10.102511405944824, 9.9550142288208, 9.887256622314453, 9.793805122375488, 9.744010925292969, 9.607592582702637, 9.518412590026855, 9.391697883605957, 9.313817024230957, 9.28628921508789, 9.259793281555176, 9.186220169067383, 9.100829124450684, 8.979741096496582, 8.908604621887207, 8.903375625610352, 8.853546142578125, 8.752199172973633, 8.746487617492676, 8.705891609191895, 8.675901412963867, 8.58354377746582, 8.586859703063965, 8.52135944366455, 8.489155769348145, 8.437057495117188, 8.398487091064453, 8.408478736877441, 8.333464622497559, 8.289693832397461, 8.247024536132812, 8.197150230407715, 8.15331840515136`

**Traços de reamostragem - triagem:** `{"x_autocorrelation": [0.9318818904219601, 0.8477977793486816, 0.7776251553140109, 0.7333359033333667, 0.7003591023472954, 0.6716139797879033, 0.6462410478045866, 0.6277276290858984, 0.6156305621458369, 0.6065562185457241, 0.6052443015797416, 0.6081250997446198, 0.5942170148650993, 0.5716973982087679, 0.5496165562282068, 0.5372476327906748, 0.5291015245328287, 0.5151187561008849, 0.49117046574250983, 0.4739612702125055, 0.4745973535347204, 0.4840186942686233, 0.4842259726158641, 0.4695174637459424, 0.4349953749068767, 0.4005384273677209, 0.3738718079738188, 0.35783012826363514, 0.34280646170941564, 0.3320946238776204, 0.3296427707680703, 0.3408037634311769], "y_autocorrelation": [0.9167956188368351, 0.8468937437713594, 0.7737292823893522, 0.7155855139479037, 0.680576857190125, 0.64891885235996, 0.6335126191451914, 0.6105609178089356, 0.5738988879918968, 0.544700939852155, 0.5144490704916`

**Residual tipo PRNU - triagem (não atribuição de câmera):** `{"residual_std": 0.03203462064266205, "local_energy_mean": 0.026883670605457155, "local_energy_cv": 0.6479464942781721, "blocks": 64, "status": "screening_only", "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}`

**Métricas de região facial - triagem:** `{"faces_detected": 1, "faces_analyzed": 1, "face_metrics": [{"bbox": [178, 67, 93, 93], "laplacian_variance": 954.4976196289062, "left_right_mean_luminance_asymmetry": 0.0931705967975007, "boundary_edge_density": 0.167045459151268, "interior_edge_density": 0.1675134301185608}], "status": "screening_only", "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them."}`

**Triagem espectral de mídia sintética:** `{"features": {"radial_profile": [13.826834678649902, 13.219463348388672, 12.545708656311035, 12.019535064697266, 11.664786338806152, 11.379905700683594, 11.181005477905273, 10.960786819458008, 10.773842811584473, 10.648115158081055, 10.467577934265137, 10.388530731201172, 10.190893173217773, 10.102511405944824, 9.9550142288208, 9.887256622314453, 9.793805122375488, 9.744010925292969, 9.607592582702637, 9.518412590026855, 9.391697883605957, 9.313817024230957, 9.28628921508789, 9.259793281555176, 9.186220169067383, 9.100829124450684, 8.979741096496582, 8.908604621887207, 8.903375625610352, 8.853546142578125, 8.752199172973633, 8.746487617492676, 8.705891609191895, 8.675901412963867, 8.58354377746582, 8.586859703063965, 8.52135944366455, 8.489155769348145, 8.437057495117188, 8.398487091064453, 8.408478736877441, 8.333464622497559, 8.289693832397461, 8.247024536132812, 8.197150230407715, 8.1`

**Tabelas de quantização JPEG:** `{"available": true, "table_count": 2, "tables": {"0": [2, 2, 1, 2, 3, 6, 7, 9, 2, 2, 2, 3, 4, 8, 8, 8, 2, 2, 2, 3, 6, 8, 10, 8, 2, 2, 3, 4, 7, 12, 11, 9, 3, 3, 5, 8, 10, 15, 14, 11, 3, 5, 8, 9, 11, 15, 16, 13, 7, 9, 11, 12, 14, 17, 17, 14, 10, 13, 13, 14, 16, 14, 14, 14], "1": [2, 3, 3, 7, 14, 14, 14, 14, 3, 3, 4, 9, 14, 14, 14, 14, 3, 4, 8, 14, 14, 14, 14, 14, 7, 9, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]}, "fingerprints": {"0": {"sum": 518, "mean": 8.09375, "min": 1, "max": 17, "first_16": [2, 2, 1, 2, 3, 6, 7, 9, 2, 2, 2, 3, 4, 8, 8, 8]}, "1": {"sum": 779, "mean": 12.171875, "min": 2, "max": 14, "first_16": [2, 3, 3, 7, 14, 14, 14, 14, 3, 3, 4, 9, 14, 14, 14, 14]}}, "warning": "Quantization tables can indicate encoding history/software families but are not unique identifiers`

**JPEG Ghost - triagem:** `{"quality_sweep": [{"quality": 55, "mean_abs_error": 3.3518245220184326, "local_cv": 0.6040078162673006}, {"quality": 60, "mean_abs_error": 3.2014365196228027, "local_cv": 0.599922933406901}, {"quality": 65, "mean_abs_error": 3.0190963745117188, "local_cv": 0.5941408731040054}, {"quality": 70, "mean_abs_error": 2.9237213134765625, "local_cv": 0.5509463726438716}, {"quality": 75, "mean_abs_error": 2.6324806213378906, "local_cv": 0.587515820187932}, {"quality": 80, "mean_abs_error": 2.346036195755005, "local_cv": 0.5712317525873293}, {"quality": 85, "mean_abs_error": 2.163926601409912, "local_cv": 0.5816406936905731}, {"quality": 90, "mean_abs_error": 1.286012053489685, "local_cv": 0.6331681090104019}, {"quality": 95, "mean_abs_error": 0.7438443899154663, "local_cv": 0.6334111650905819}, {"quality": 100, "mean_abs_error": 0.4080454707145691, "local_cv": 0.9099905098819003}], "minimum_error`

**Periodicidade DCT / dupla compressão - heurística:** `{"score": 0.12870045936001911, "n_blocks": 4096, "zero_bin_fraction": 0.09395973154362416, "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}`

**Copy-move por características ORB - triagem:** `{"keypoints": 2496, "suspicious_pairs": 0, "score": 0.0, "warning": "Feature matching is a screening detector; repetitive textures can cause false positives."}`

**Esteganálise LSB - triagem:** `{"channels": {"R": {"n0": 142450, "n1": 119694, "p1": 0.45659637451171875, "entropy_bits": 0.9945574391465818, "chi2": 1975.3858032226562, "pvalue": 0.0}, "G": {"n0": 144357, "n1": 117787, "p1": 0.4493217468261719, "entropy_bits": 0.9925767543168789, "chi2": 2693.0423736572266, "pvalue": 0.0}, "B": {"n0": 146958, "n1": 115186, "p1": 0.43939971923828125, "entropy_bits": 0.9893776145499938, "chi2": 3850.7842407226562, "pvalue": 0.0}}, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}`

**Protocolo MFLAB-DF para imagem:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "needs_expert_review", "evidence_families": [{"family": "frequency", "signals": ["high_spectral_quadrant_symmetry"], "strength": "screening"}, {"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"}], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### vid_001_pristine.mp4
SHA-256: `a30ec9df06f581cd52243db14357dfee1e8e8aeec7778bf4b6f196e7ca5a383e`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=no_strong_screening_signals; famílias de evidência sinalizadas=0; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "a30ec9df06f581cd52243db14357dfee1e8e8aeec7778bf4b6f196e7ca5a383e"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "video", "streams": 1, "format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.000000"}`

**Estrutura temporal / timestamps:** `{"frame_count": 72, "timestamp_count": 72, "large_gaps": [], "i_frames": 6}`

**Frames adjacentes quase duplicados:** `{"frame_count": 72, "adjacent_near_duplicates": [], "duplicate_count": 0, "mad_threshold": 0.05, "median_adjacent_mad": 0.20361328125}`

**Protocolo MFLAB-DF para vídeo:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "no_strong_screening_signals", "evidence_families": [], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### vid_002_duplicated_frames.mp4
SHA-256: `0b56f94aedc4d5c19f315e05e618f9e472433e4e63f47dab2ff4d781db4ed08d`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=no_strong_screening_signals; famílias de evidência sinalizadas=0; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "0b56f94aedc4d5c19f315e05e618f9e472433e4e63f47dab2ff4d781db4ed08d"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "video", "streams": 1, "format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.208333"}`

**Estrutura temporal / timestamps:** `{"frame_count": 77, "timestamp_count": 77, "large_gaps": [], "i_frames": 7}`

**Frames adjacentes quase duplicados:** `{"frame_count": 77, "adjacent_near_duplicates": [36, 37, 38, 39, 40], "duplicate_count": 5, "mad_threshold": 0.05, "median_adjacent_mad": 0.189697265625}`

**Protocolo MFLAB-DF para vídeo:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "no_strong_screening_signals", "evidence_families": [], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### vid_003_deleted_segment.mp4
SHA-256: `595f48e2b0cf785e5583c74f11edce68f3b32cc683dd9b2a5fb1bc30f8656753`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=no_strong_screening_signals; famílias de evidência sinalizadas=0; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "595f48e2b0cf785e5583c74f11edce68f3b32cc683dd9b2a5fb1bc30f8656753"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "video", "streams": 1, "format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.583333"}`

**Estrutura temporal / timestamps:** `{"frame_count": 62, "timestamp_count": 62, "large_gaps": [], "i_frames": 6}`

**Frames adjacentes quase duplicados:** `{"frame_count": 62, "adjacent_near_duplicates": [], "duplicate_count": 0, "mad_threshold": 0.05, "median_adjacent_mad": 0.216552734375}`

**Protocolo MFLAB-DF para vídeo:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "no_strong_screening_signals", "evidence_families": [], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

### vid_004_overlay_edit.mp4
SHA-256: `99bce14c3037eceb0da5c73c7ca08c748706e0092d4ae116e6cc69a59a66025e`

**Resumo deepfake:** MFLAB-DF-0.2: triagem=no_strong_screening_signals; famílias de evidência sinalizadas=0; modelos externos explicitamente marcados como validados=0; conclusão automática de valor probatório=inconclusive.

**Hash criptográfico SHA-256:** `{"sha256": "99bce14c3037eceb0da5c73c7ca08c748706e0092d4ae116e6cc69a59a66025e"}`

**Proveniência C2PA / Content Credentials:** `{"status": "unavailable", "tool": "c2patool", "reason": "c2patool_not_found", "note": "Install the official C2PA CLI to enable cryptographic provenance validation."}`

**Metadados e estrutura técnica:** `{"kind": "video", "streams": 1, "format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.000000"}`

**Estrutura temporal / timestamps:** `{"frame_count": 72, "timestamp_count": 72, "large_gaps": [], "i_frames": 6}`

**Frames adjacentes quase duplicados:** `{"frame_count": 72, "adjacent_near_duplicates": [], "duplicate_count": 0, "mad_threshold": 0.05, "median_adjacent_mad": 0.201416015625}`

**Protocolo MFLAB-DF para vídeo:** `{"protocol_version": "MFLAB-DF-0.2", "triage_assessment": "no_strong_screening_signals", "evidence_families": [], "validated_external_models": 0, "evidentiary_conclusion": "inconclusive"}`

## 6. Conclusão preliminar
Foram observados achados que justificam exame aprofundado: img_001_pristine.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_002_copy_move.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_003_splice.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_004_double_jpeg.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_005_resampled.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_006_inpainted.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. vid_002_duplicated_frames.mp4: 5 transição(ões) entre frames adjacentes atingiram o limiar de quase-duplicação e exigem confirmação visual.

## 7. Respostas aos quesitos
- **Quesito:** Há indícios técnicos de alteração ou manipulação do conteúdo?
  - **Resposta:** Foram observados achados que justificam exame aprofundado: img_001_pristine.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_002_copy_move.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_003_splice.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_004_double_jpeg.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_005_resampled.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. img_006_inpainted.jpg: o protocolo MFLAB-DF-0.2 identificou sinais que justificam revisão pericial aprofundada, sem classificá-los isoladamente como deepfake/IA. vid_002_duplicated_frames.mp4: 5 transição(ões) entre frames adjacentes atingiram o limiar de quase-duplicação e exigem confirmação visual.
- **Quesito:** Os metadados e a estrutura do arquivo são compatíveis com a narrativa de origem apresentada?
  - **Resposta:** O laboratório registra e descreve metadados, estrutura e proveniência disponível, mas a compatibilidade com uma narrativa de origem depende de informação externa documentada e, quando possível, confronto com o arquivo/dispositivo fonte. Metadados ausentes ou editáveis não bastam, isoladamente, para confirmar ou negar a narrativa.
- **Quesito:** Há elementos suficientes para afirmar ou excluir geração sintética/IA?
  - **Resposta:** Foram executados 10 protocolo(s) MFLAB-DF; 6 indicou(aram) necessidade de revisão aprofundada e 0 saída(s) de modelo externo foram explicitamente marcadas como validadas no caso. O pipeline não converte heurísticas ou um único escore em certeza. Assim, salvo convergência adicional documentada por especialista, o resultado automático permanece inconclusivo quanto à geração sintética/IA.

## 8. Limitações
Este documento é preliminar. A ausência de artefatos detectáveis não prova autenticidade. Metadados podem ser alterados; recompressão e plataformas podem apagar/criar sinais; detectores de IA sofrem com mudança de domínio e geradores desconhecidos. ELA, PRNU simplificado, análise espectral e outros heurísticos devem ser corroborados por métodos validados e revisão humana.

## 9. Referências
- C2PA. Coalition for Content Provenance and Authenticity. C2PA Technical Specification, version 2.4, 2026.
- LI, Y. et al. Celeb-DF: A Large-Scale Challenging Dataset for DeepFake Forensics. CVPR, 2020.
- BRASIL. Lei nº 13.105, de 16 de março de 2015. Código de Processo Civil, art. 473. Texto atualizado. Câmara dos Deputados.
- BRASIL. Decreto-Lei nº 3.689, de 3 de outubro de 1941. Código de Processo Penal, arts. 158-A a 158-F. Texto atualizado. Câmara dos Deputados.
- YAN, Z. et al. DeepfakeBench: A Comprehensive Benchmark of Deepfake Detection. NeurIPS Datasets and Benchmarks, 2023.
- DURALL, R.; KEUPER, M.; KEUPER, J. Watch Your Up-Convolution: CNN Based Generative Deep Neural Networks Are Failing to Reproduce Spectral Distributions. CVPR, 2020.
- RÖSSLER, A. et al. FaceForensics++: Learning to Detect Manipulated Facial Images. ICCV, 2019.
- FARID, H. Photo Forensics. MIT Press, 2016.
- FRIDRICH, J.; SOUKAL, D.; LUKÁŠ, J. Detection of Copy-Move Forgery in Digital Images. DFRWS, 2003.
- FRIDRICH, J. Steganography in Digital Media: Principles, Algorithms, and Applications. Cambridge University Press, 2010.
- LUKÁŠ, J.; FRIDRICH, J. Estimation of Primary Quantization Matrix in Double Compressed JPEG Images. DFRWS, 2003.
- LUKÁŠ, J.; FRIDRICH, J.; GOLJAN, M. Determining Digital Image Origin Using Sensor Imperfections. Proc. SPIE, 2005.
- POPESCU, A. C.; FARID, H. Exposing Digital Forgeries by Detecting Traces of Resampling. IEEE Transactions on Signal Processing, v. 53, n. 2, p. 758-767, 2005.
- SWGDE. Technical Notes on FFmpeg for Forensic Video Examinations. 16-V-002-3.0, 2024.
- SWGDE. Best Practices for Image Authentication. 18-I-001-2.0, version 2.0, 2025.
- SWGDE. Best Practices for Maintaining the Integrity of Imagery. 17-I-001-1.1.
- SWGDE. Best Practices for Digital Video Authentication. 23-V-001-1.2, 2024.
- GUILLARO, F. et al. TruFor: Leveraging All-Round Clues for Trustworthy Image Forgery Detection and Localization. CVPR, 2023.
- VERDOLIVA, L. Media Forensics and DeepFakes: an overview. IEEE Journal of Selected Topics in Signal Processing, 2020.