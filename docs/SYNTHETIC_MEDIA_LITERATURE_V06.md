# Literatura incorporada ao ramo de mídia sintética — v0.6

A v0.6 fortalece o MFLab a partir de uma estratégia híbrida: features forenses explicáveis + classificadores aprendidos + detector profundo opcional + proveniência + convergência pericial.

## Say, Alkan e Kocak (2025)

**Advancing GAN Deepfake Detection: Mixed Datasets and Comprehensive Artifact Analysis. Applied Sciences, 15(2), 923. DOI 10.3390/app15020923.**

O trabalho combina Fourier, wavelet, HOG e correlações RGB com múltiplos classificadores e enfatiza diversidade de GANs e generalização. A v0.6 implementa diretamente essas quatro famílias no `synthetic_handcrafted_v1` e cria uma camada de benchmark com Logistic Regression, SVM-RBF, ExtraTrees e HistGradientBoosting.

## Wyawahare et al. (2025)

**Comparative Analysis of Deepfake Detection Models on Diverse GAN-Generated Images. International Journal of Electrical and Computer Engineering Systems, 16(1), 9–18. DOI 10.32985/ijeces.16.1.2.**

O estudo compara VGG16, ResNet50, VGG19 e MobileNetV2 em imagens StyleGAN2, StyleGAN3 e ProGAN, reforçando que o desempenho depende do gerador. O MFLab responde a isso separando avaliação por `generator`, adicionando leave-one-generator-out e oferecendo um adaptador profundo ONNX independente da arquitetura.

## Sao et al. (2025)

**Detecting GAN-Generated Fake Images Using Deep Learning and Feature Analysis. 2025 International Conference on Intelligent and Cloud Computing (ICoICC), IEEE. DOI 10.1109/ICoICC64033.2025.11052138.**

A publicação é tratada no projeto como evidência adicional da utilidade de combinar deep learning e feature analysis. A v0.6 não incorpora um checkpoint específico desse trabalho; em vez disso, cria um contrato explícito para modelos profundos externos/ONNX e preserva a exigência de validação documental.

## Limite metodológico

Resultados altos dentro de um dataset GAN não são automaticamente transferíveis para geradores não vistos, diffusion, imagens recomprimidas ou screenshots. Por isso o benchmark científico do MFLab registra desempenho por gerador e transformação e mantém o GT pequeno do CI separado da avaliação populacional.
