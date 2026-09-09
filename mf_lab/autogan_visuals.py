from __future__ import annotations

import re
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mf_lab.analysis.autogan_spectral import AUTOGAN_MODES, autogan_visual_spectrum


def _slug(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", text).strip("._")
    return value or "media"


def _row(root: Path, path: Path, artifact_id: str, label: str, caption: str, warning: str) -> dict:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return {
        "id": artifact_id,
        "label": label,
        "method": "autogan_spectral",
        "category": "deepfake_gan_spectral",
        "path": rel,
        "caption": caption,
        "warning": warning,
    }


def _save_spectrum(media: Path, out: Path, mode: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rgb = autogan_visual_spectrum(media, mode=mode)
    Image.fromarray(rgb, mode="RGB").save(out, format="PNG")


def _profile_chart(result: dict, out: Path) -> None:
    f = result.get("features") or {}
    labels = ["low", "mid", "high"]
    fractions = [float(f.get(f"autogan_{name}_energy_fraction", 0.0) or 0.0) for name in labels]
    replication = [
        float(f.get("autogan_replication_autocorr_peak_x", 0.0) or 0.0),
        float(f.get("autogan_replication_autocorr_peak_y", 0.0) or 0.0),
        float(f.get("autogan_quadrant_replication_score", 0.0) or 0.0),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    axes[0].bar(labels, fractions)
    axes[0].set_title("Energia espectral por banda")
    axes[0].set_ylabel("Fração descritiva")
    axes[1].bar(["AC-X", "AC-Y", "quadrantes"], replication)
    axes[1].set_title("Descritores de replicação espectral")
    axes[1].set_ylabel("Índice descritivo")
    fig.suptitle("AutoGAN-compatible spectral profile")
    fig.savefig(out, dpi=150)
    plt.close(fig)


def generate_autogan_visual_artifacts(media_path: str | Path, case_root: str | Path, result: dict) -> dict:
    """Render AutoGAN-compatible explanatory visuals for the generic v0.7 gallery.

    Returned rows use the same artifact schema as the existing visual layer, so
    the website and DOCX appendix can display them without a visual redesign.
    """
    media = Path(media_path)
    root = Path(case_root)
    if result.get("status") != "success":
        return {"status": "not_available", "artifact_count": 0, "items": [], "errors": []}

    out_dir = root / "visuals" / _slug(media.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    errors = []
    warning = (
        "Esta visualização destaca descritores espectrais associados a pipelines GAN; saliência visual não prova geração por IA e a ausência do padrão não exclui diffusion ou outros geradores."
    )

    labels = {
        "full": "AutoGAN — espectro completo",
        "low": "AutoGAN — banda de baixa frequência",
        "mid": "AutoGAN — banda de média frequência",
        "high": "AutoGAN — banda de alta frequência",
    }
    for mode in AUTOGAN_MODES:
        target = out_dir / f"autogan_fft_{mode}.png"
        try:
            _save_spectrum(media, target, mode)
            items.append(_row(
                root,
                target,
                f"autogan_fft_{mode}",
                labels[mode],
                f"Magnitude FFT por canal após normalização P5/P95 e seleção da banda {mode}, compatível com o pré-processamento científico do AutoGAN.",
                warning,
            ))
        except Exception as exc:
            errors.append({"id": f"autogan_fft_{mode}", "error": repr(exc)})

    profile = out_dir / "autogan_spectral_profile.png"
    try:
        _profile_chart(result, profile)
        items.append(_row(
            root,
            profile,
            "autogan_spectral_profile",
            "AutoGAN — perfil espectral descritivo",
            "Resumo das frações de energia por banda e índices descritivos de repetição do espectro.",
            "Os índices não possuem limiar universal validado e não são probabilidades de mídia sintética.",
        ))
    except Exception as exc:
        errors.append({"id": "autogan_spectral_profile", "error": repr(exc)})

    return {
        "status": "success" if items else "no_artifacts",
        "artifact_count": len(items),
        "items": items,
        "errors": errors,
    }
