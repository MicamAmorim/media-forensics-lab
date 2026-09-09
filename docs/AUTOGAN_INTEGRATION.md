# AutoGAN-compatible spectral integration — MFLab v0.8

## Objective

MFLab v0.8 adds a GAN-specific spectral family inspired by Zhang, Karaman and Chang, *Detecting and Simulating Artifacts in GAN Fake Images* (WIFS 2019). The original work argues that upsampling operations shared by several GAN pipelines can create spectral replications and proposes classification from frequency-domain inputs.

The MFLab implementation is intentionally split into two components:

1. **`autogan_spectral`** — native, dependency-light, descriptive clean-room implementation of the spectral preprocessing and frequency partitions;
2. **`autogan_classifier`** — optional adapter for an explicitly configured ResNet34 checkpoint compatible with the AutoGAN spectral input convention.

No upstream model weight is bundled and no AutoGAN score is promoted to a forensic verdict by default.

## Native preprocessing

For each RGB channel, MFLab:

1. converts/resizes the image to 256×256;
2. takes the central 224×224 crop used by the ResNet-family detector pipeline;
3. computes the 2D FFT;
4. computes `log(abs(FFT) + 1e-3)`;
5. estimates the 5th and 95th percentiles;
6. maps that interval to `[-1, 1]` and clips outside it;
7. optionally retains the `full`, `low`, `mid` or `high` frequency partition in the centered frequency plane.

For the canonical 224×224 crop, the low/mid/high boundaries are compatible with the public AutoGAN implementation:

- low: central `[57:177, 57:177]` region;
- mid: `[21:203, 21:203]` excluding the low region;
- high: frequencies outside `[21:203, 21:203]`.

These three partitions are disjoint and reconstruct the full normalized spectral tensor when summed.

## Descriptive features

`autogan_spectral` records, without a fake/real threshold:

- mean absolute spectral magnitude and standard deviation for full/low/mid/high modes;
- low/mid/high energy fractions;
- autocorrelation peak and lag for horizontal/vertical spectral profiles;
- average absolute cross-quadrant correlation;
- per-channel spectral mean, standard deviation and absolute P95.

The resulting keys are prefixed `autogan_` and are also included in `synthetic_handcrafted_v2`, allowing the scientific benchmark and optional handcrafted ML model to combine them with wavelet, HOG, RGB, GLCM/LBP and the existing MFLab FFT features.

## Optional checkpoint adapter

Install the optional runtime:

```powershell
python -m pip install -e .[autogan]
```

Configure a compatible checkpoint:

```powershell
$env:MFLAB_AUTOGAN_CHECKPOINT="C:\modelos\autogan\checkpoint_10.pth"
$env:MFLAB_AUTOGAN_FEATURE_MODE="full"
```

Supported feature modes are `full`, `low`, `mid` and `high`.

The adapter creates a modern Torchvision ResNet34 with two output classes and loads a compatible state dict. The label convention follows the published AutoGAN dataset code: class `0` is synthetic/fake and class `1` is real. Therefore `score_synthetic` is softmax class 0.

The checkpoint SHA-256 is recorded in every successful result.

## Validation metadata

A checkpoint is **not** validated merely because it loads or produces a high score. Optional metadata can be supplied beside the checkpoint (`checkpoint.pth.json` or `checkpoint.json`) or through `MFLAB_AUTOGAN_METADATA`.

Example:

```json
{
  "model_name": "autogan_resnet34_fft",
  "validated": false,
  "calibrated": false,
  "validation": {
    "protocol": "MFLAB-SCI-SYNTH-0.3",
    "report": "validation/scientific/autogan.json"
  }
}
```

`validated: true` should only be used after a documented independent evaluation that establishes the relevant domain, split policy, error rates and robustness conditions.

## Scientific benchmark

`mflab benchmark-synthetic` now:

- includes AutoGAN-compatible descriptors in the handcrafted feature matrix;
- reports their names/count separately;
- continues selecting the handcrafted classifier without touching the final test set;
- evaluates a configured AutoGAN checkpoint separately on the untouched final test split;
- records fixed-checkpoint metrics globally, by generator and by transformation;
- preserves leave-one-generator-out evaluation for the learned handcrafted branch.

Recommended experimental blocks include:

- within-generator GAN evaluation;
- leave-one-generator-out GAN evaluation;
- GAN → diffusion cross-family testing;
- JPEG, resize, screenshot and social-media re-encoding robustness;
- explicit FPR and specificity analysis on real images.

## Visual artifacts

Without changing the site design, each successful image analysis adds:

- `autogan_fft_full.png`;
- `autogan_fft_low.png`;
- `autogan_fft_mid.png`;
- `autogan_fft_high.png`;
- `autogan_spectral_profile.png`.

They use the existing v0.7 artifact schema and therefore appear automatically in the **Gráficos e imagens** tab and the DOCX/Markdown **Apêndice A**.

These figures are explanatory derivatives. Visual regularity or salience is not proof of GAN generation.

## Evidentiary policy

`MFLAB-DF-0.6` maintains the following rules:

- execution of `autogan_spectral` alone does not create an independent evidence family;
- an unvalidated positive `autogan_classifier` result is a screening observation only;
- a checkpoint explicitly documented as validated may participate as one model family in the convergence summary;
- the automatic `evidentiary_conclusion` remains `inconclusive`;
- a negative AutoGAN-family result does **not** establish authenticity;
- the method does not claim universal coverage of diffusion or other non-GAN generators.

## Reproducibility and source separation

The official AutoGAN repository uses a historical Python/PyTorch/CUDA stack. MFLab does not import that environment into the core package. The native spectral implementation is maintained against the current MFLab Python 3.10–3.12 CI matrix, while Torch/Torchvision remain optional for checkpoint compatibility.
