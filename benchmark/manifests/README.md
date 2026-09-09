# Manifestos de benchmark

Não armazene datasets científicos grandes no Git. Armazene apenas manifestos de exemplo, scripts de aquisição, versões e checksums quando a licença permitir.

Colunas recomendadas: `path,label,generator,split,transform`.

- `label`: `real` ou `synthetic`.
- `split`: `train` ou `test`.
- `generator`: `camera`, `StyleGAN2`, `StyleGAN3`, `ProGAN`, `diffusion-*`, `faceswap-*` etc.
- `transform`: `original`, `jpeg_q70`, `resize_0.5`, `screenshot`, `social_reencode` etc.
