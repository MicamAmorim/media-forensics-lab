from __future__ import annotations

import io
import re
from pathlib import Path

import cv2
import matplotlib
import numpy as np
from PIL import Image, ImageChops, ImageDraw

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mf_lab.utils.io import cv_imread


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".heic", ".heif"}
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts"}


def _slug(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", text).strip("._")
    return value or "media"


def _normalize_u8(arr: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    x = np.asarray(arr, dtype=np.float32)
    if not np.isfinite(x).any():
        return np.zeros(x.shape, dtype=np.uint8)
    a, b = np.nanpercentile(x, [lo, hi])
    if not np.isfinite(a) or not np.isfinite(b) or b <= a:
        a, b = float(np.nanmin(x)), float(np.nanmax(x))
    if b <= a:
        return np.zeros(x.shape, dtype=np.uint8)
    return np.clip((x - a) / (b - a) * 255.0, 0, 255).astype(np.uint8)


def _save_rgb(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB").save(path, format="PNG")


def _artifact(case_root: Path, path: Path, artifact_id: str, label: str, method: str,
              category: str, caption: str, warning: str | None = None) -> dict:
    try:
        rel = path.relative_to(case_root).as_posix()
    except ValueError:
        rel = path.as_posix()
    row = {
        "id": artifact_id,
        "label": label,
        "method": method,
        "category": category,
        "path": rel,
        "caption": caption,
    }
    if warning:
        row["warning"] = warning
    return row


def _ela_artifact(media: Path, out: Path, quality: int = 90) -> None:
    with Image.open(media) as im0:
        im = im0.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=int(quality))
        buf.seek(0)
        rec = Image.open(buf).convert("RGB")
        diff = np.asarray(ImageChops.difference(im, rec), dtype=np.float32)
    maxv = float(diff.max())
    scale = min(25.0, 255.0 / max(maxv, 1.0))
    vis = np.clip(diff * scale, 0, 255).astype(np.uint8)
    _save_rgb(out, vis)


def _noise_artifact(media: Path, out: Path) -> None:
    gray = cv_imread(media, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("unreadable image")
    x = gray.astype(np.float32) / 255.0
    residual = x - cv2.GaussianBlur(x, (0, 0), 1.2)
    vis = _normalize_u8(np.abs(residual), 2.0, 99.5)
    _save_rgb(out, np.dstack([vis, vis, vis]))


def _fft_artifact(media: Path, out: Path) -> None:
    gray = cv_imread(media, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("unreadable image")
    x = gray.astype(np.float32) - float(gray.mean())
    mag = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(x))))
    vis = _normalize_u8(mag, 1.0, 99.8)
    _save_rgb(out, np.dstack([vis, vis, vis]))


def _rgb_histogram_artifact(media: Path, out: Path) -> None:
    bgr = cv_imread(media, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("unreadable image")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    fig = plt.figure(figsize=(8, 4.5), constrained_layout=True)
    ax = fig.add_subplot(111)
    for idx, name in enumerate(("R", "G", "B")):
        hist = cv2.calcHist([rgb[:, :, idx]], [0], None, [256], [0, 256]).ravel()
        ax.plot(np.arange(256), hist, label=name)
    ax.set_title("Histograma RGB")
    ax.set_xlabel("Intensidade")
    ax.set_ylabel("Contagem")
    ax.set_xlim(0, 255)
    ax.legend()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _jpeg_ghost_curve(result: dict, out: Path) -> None:
    rows = result.get("quality_sweep") or []
    if not rows:
        raise ValueError("no JPEG ghost sweep")
    q = [r.get("quality") for r in rows]
    err = [r.get("mean_abs_error") for r in rows]
    cv = [r.get("local_cv") for r in rows]
    fig = plt.figure(figsize=(8, 4.5), constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.plot(q, err, marker="o", label="erro médio absoluto")
    ax.set_xlabel("Qualidade JPEG de recompressão")
    ax.set_ylabel("Erro médio absoluto")
    ax2 = ax.twinx()
    ax2.plot(q, cv, marker="x", linestyle="--", label="CV local")
    ax2.set_ylabel("Coeficiente de variação local")
    ax.set_title("Varredura JPEG Ghost")
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _resampling_curve(result: dict, out: Path) -> None:
    axv = result.get("x_autocorrelation") or []
    ayv = result.get("y_autocorrelation") or []
    if not axv and not ayv:
        raise ValueError("no resampling autocorrelation")
    fig = plt.figure(figsize=(8, 4.5), constrained_layout=True)
    ax = fig.add_subplot(111)
    if axv:
        ax.plot(range(1, len(axv) + 1), axv, marker="o", label="eixo X")
    if ayv:
        ax.plot(range(1, len(ayv) + 1), ayv, marker="x", label="eixo Y")
    ax.set_title("Autocorrelação para triagem de reamostragem")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Autocorrelação")
    ax.legend()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _copy_move_overlay(media: Path, result: dict, out: Path) -> None:
    with Image.open(media) as im0:
        im = im0.convert("RGB")
    draw = ImageDraw.Draw(im)
    suspicious = [r for r in (result.get("translation_clusters") or []) if r.get("suspicious")]
    if not suspicious:
        raise ValueError("no suspicious copy-move cluster")
    for i, row in enumerate(suspicious[:6], 1):
        a = row.get("source_bbox") or []
        b = row.get("destination_bbox") or []
        if len(a) != 4 or len(b) != 4:
            continue
        draw.rectangle(tuple(a), outline=(255, 215, 0), width=4)
        draw.rectangle(tuple(b), outline=(255, 80, 80), width=4)
        ac = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
        bc = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        draw.line([ac, bc], fill=(80, 220, 255), width=3)
        draw.text((a[0], max(0, a[1] - 14)), f"origem {i}", fill=(255, 215, 0))
        draw.text((b[0], max(0, b[1] - 14)), f"destino {i}", fill=(255, 80, 80))
    im.save(out, format="PNG")


def _face_context_overlay(media: Path, result: dict, out: Path) -> None:
    with Image.open(media) as im0:
        im = im0.convert("RGB")
    draw = ImageDraw.Draw(im)
    rows = result.get("face_context_metrics") or []
    if not rows:
        raise ValueError("no analyzed face")
    W, H = im.size
    for i, row in enumerate(rows[:10], 1):
        x, y, w, h = [int(v) for v in row.get("bbox", [0, 0, 0, 0])]
        pad_x, pad_y = max(8, w // 3), max(8, h // 3)
        context = (max(0, x - pad_x), max(0, y - pad_y), min(W - 1, x + w + pad_x), min(H - 1, y + h + pad_y))
        draw.rectangle(context, outline=(80, 220, 255), width=3)
        draw.rectangle((x, y, x + w, y + h), outline=(255, 190, 70), width=4)
        nr = row.get("face_context_noise_ratio")
        sr = row.get("face_context_sharpness_ratio")
        txt = f"face {i} | noise={nr:.2f} sharp={sr:.2f}" if isinstance(nr, (int, float)) and isinstance(sr, (int, float)) else f"face {i}"
        draw.text((x, max(0, y - 16)), txt, fill=(255, 230, 160))
    im.save(out, format="PNG")


def _reference_difference(media: Path, reference: Path, out: Path, result: dict | None = None) -> None:
    q = cv_imread(media, cv2.IMREAD_COLOR)
    r = cv_imread(reference, cv2.IMREAD_COLOR)
    if q is None or r is None:
        raise ValueError("unreadable image/reference")
    if q.shape != r.shape:
        raise ValueError("reference dimensions differ")
    diff = np.mean(np.abs(q.astype(np.float32) - r.astype(np.float32)), axis=2)
    heat = _normalize_u8(diff, 1.0, 99.5)
    rgb = cv2.applyColorMap(heat, cv2.COLORMAP_INFERNO)
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    if isinstance(result, dict):
        bbox = result.get("largest_component_bbox_xywh")
        if bbox and len(bbox) == 4:
            x, y, w, h = [int(v) for v in bbox]
            cv2.rectangle(rgb, (x, y), (x + w, y + h), (255, 255, 255), 3)
    _save_rgb(out, rgb)


def _synthetic_feature_profile(result: dict, out: Path) -> None:
    f = result.get("features") or {}
    if not f:
        raise ValueError("no synthetic feature bank")
    wavelet_keys = [k for k in f if k.startswith("wavelet_") and k.endswith("hf_total")]
    fft_keys = [k for k in f if k.startswith("fft_band_")]
    rgb_keys = [k for k in ("rgb_corr_rg", "rgb_corr_rb", "rgb_corr_gb") if k in f]
    texture_keys = [k for k in ("glcm_contrast", "glcm_homogeneity", "glcm_energy", "glcm_correlation", "hog_mean", "hog_std") if k in f]
    groups = [("Wavelet HF", wavelet_keys), ("FFT multibanda", fft_keys), ("Correlação RGB", rgb_keys), ("Textura/HOG", texture_keys)]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for ax, (title, keys) in zip(axes.ravel(), groups):
        vals = [float(f[k]) for k in keys]
        labels = [k.replace("wavelet_", "").replace("fft_", "").replace("rgb_corr_", "").replace("glcm_", "") for k in keys]
        ax.bar(range(len(vals)), vals)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Perfil descritivo de características para mídia sintética")
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _video_series(media: Path) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    cap = cv2.VideoCapture(str(media))
    previous64 = None
    previous128 = None
    mad = []
    flow = []
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if len(frames) < 400:
            frames.append(frame.copy())
        g64 = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        g128 = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (128, 128), interpolation=cv2.INTER_AREA)
        if previous64 is not None:
            mad.append(float(np.mean(np.abs(g64 - previous64))))
        if previous128 is not None:
            ff = cv2.calcOpticalFlowFarneback(previous128, g128, None, 0.5, 3, 21, 3, 5, 1.2, 0)
            flow.append(float(np.mean(np.linalg.norm(ff, axis=2))))
        previous64, previous128 = g64, g128
    cap.release()
    return np.asarray(mad, dtype=float), np.asarray(flow, dtype=float), frames


def _video_transition_chart(mad: np.ndarray, methods: dict, out: Path) -> None:
    if mad.size == 0:
        raise ValueError("video has no transitions")
    transition = methods.get("video_transition_anomalies") or {}
    dup = methods.get("video_duplicates") or {}
    fig = plt.figure(figsize=(10, 4.5), constrained_layout=True)
    ax = fig.add_subplot(111)
    x = np.arange(1, len(mad) + 1)
    ax.plot(x, mad, label="MAD frame a frame")
    threshold = transition.get("threshold")
    if isinstance(threshold, (int, float)):
        ax.axhline(float(threshold), linestyle="--", label="limiar transição")
    for idx in transition.get("anomalous_transitions") or []:
        ax.axvline(int(idx.get("index", 0)), alpha=0.35)
    for idx in dup.get("adjacent_near_duplicates") or []:
        ax.scatter([int(idx)], [mad[max(0, int(idx) - 1)] if int(idx) - 1 < len(mad) else 0], marker="x")
    ax.set_title("Timeline de diferenças entre frames")
    ax.set_xlabel("Índice da transição")
    ax.set_ylabel("MAD normalizado")
    ax.legend()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _video_motion_chart(flow: np.ndarray, methods: dict, out: Path) -> None:
    if flow.size == 0:
        raise ValueError("video has no optical flow")
    motion = methods.get("video_motion_discontinuities") or {}
    fig = plt.figure(figsize=(10, 4.5), constrained_layout=True)
    ax = fig.add_subplot(111)
    x = np.arange(1, len(flow) + 1)
    ax.plot(x, flow, label="fluxo óptico médio")
    for row in motion.get("anomalies") or []:
        ax.axvline(int(row.get("index", 0)), alpha=0.35)
    ax.set_title("Timeline de descontinuidade de movimento")
    ax.set_xlabel("Índice da transição")
    ax.set_ylabel("Magnitude média do fluxo")
    ax.legend()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _video_keyframes(frames: list[np.ndarray], methods: dict, out: Path) -> None:
    idx = set()
    for row in (methods.get("video_transition_anomalies") or {}).get("anomalous_transitions") or []:
        idx.add(int(row.get("index", 0)))
    for row in (methods.get("video_motion_discontinuities") or {}).get("anomalies") or []:
        idx.add(int(row.get("index", 0)))
    for i in (methods.get("video_duplicates") or {}).get("adjacent_near_duplicates") or []:
        idx.add(int(i))
    idx = sorted(i for i in idx if 0 <= i < len(frames))[:12]
    if not idx:
        return
    thumbs = []
    for i in idx:
        rgb = cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb).resize((320, 180))
        canvas = Image.new("RGB", (320, 205), "black")
        canvas.paste(im, (0, 0))
        ImageDraw.Draw(canvas).text((8, 185), f"frame {i}", fill="white")
        thumbs.append(canvas)
    cols = 3
    rows = int(np.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 320, rows * 205), "black")
    for n, im in enumerate(thumbs):
        sheet.paste(im, ((n % cols) * 320, (n // cols) * 205))
    sheet.save(out, format="PNG")


def generate_visual_artifacts(media_path: str | Path, case_root: str | Path, methods: dict,
                              reference_path: str | Path | None = None) -> dict:
    """Render explainable PNG artifacts without changing analytic decisions.

    Visuals are derivative examination aids. They make numerical findings easier
    to inspect and report, but they do not create a new evidence family and must
    not be interpreted as proof merely because a region appears salient.
    """
    media = Path(media_path)
    root = Path(case_root)
    media_dir = root / "visuals" / _slug(media.name)
    media_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    errors: list[dict] = []

    def run(artifact_id: str, filename: str, label: str, method: str, category: str,
            caption: str, fn, warning: str | None = None) -> None:
        target = media_dir / filename
        try:
            fn(target)
            items.append(_artifact(root, target, artifact_id, label, method, category, caption, warning))
        except Exception as exc:
            errors.append({"id": artifact_id, "error": repr(exc)})

    ext = media.suffix.lower()
    if ext in _IMAGE_EXTS or ext not in _VIDEO_EXTS:
        if isinstance(methods.get("ela"), dict) and methods["ela"].get("status") != "error":
            q = int(methods["ela"].get("quality", 90) or 90)
            run("ela", "ela.png", "Error Level Analysis", "ela", "compressao",
                "Diferença após recompressão JPEG, amplificada apenas para visualização.",
                lambda p: _ela_artifact(media, p, q),
                "ELA é exploratório e não demonstra manipulação isoladamente.")
        run("noise_residual", "noise_residual.png", "Mapa de residual de ruído", "noise_map", "ruido_sensor",
            "Magnitude do residual de alta frequência após suavização gaussiana.",
            lambda p: _noise_artifact(media, p),
            "Textura, denoising, HDR e recompressão também alteram este mapa.")
        if isinstance(methods.get("frequency"), dict) and methods["frequency"].get("status") != "error":
            run("fft_spectrum", "fft_spectrum.png", "Espectro FFT", "frequency", "frequencia",
                "Magnitude logarítmica do espectro bidimensional centralizado.",
                lambda p: _fft_artifact(media, p),
                "Padrões espectrais são dependentes de modelo e pós-processamento.")
        if isinstance(methods.get("histogram"), dict) and methods["histogram"].get("status") != "error":
            run("rgb_histogram", "rgb_histogram.png", "Histograma RGB", "histogram", "cor",
                "Distribuição descritiva das intensidades nos canais RGB.",
                lambda p: _rgb_histogram_artifact(media, p))
        ghost = methods.get("jpeg_ghost") or {}
        if ghost.get("quality_sweep"):
            run("jpeg_ghost_curve", "jpeg_ghost_curve.png", "Curva JPEG Ghost", "jpeg_ghost", "compressao",
                "Erro de recompressão e variação local ao longo de diferentes qualidades JPEG.",
                lambda p: _jpeg_ghost_curve(ghost, p),
                "Mínimos de erro podem decorrer de recompressão legítima.")
        resampling = methods.get("resampling") or {}
        if resampling.get("x_autocorrelation") or resampling.get("y_autocorrelation"):
            run("resampling_autocorrelation", "resampling_autocorrelation.png", "Autocorrelação de reamostragem", "resampling", "reamostragem",
                "Autocorrelação das derivadas usada como triagem de interpolação/reamostragem.",
                lambda p: _resampling_curve(resampling, p),
                "É uma heurística de triagem e requer confirmação independente.")
        cm = methods.get("copy_move_orb") or {}
        if cm.get("suspicious_cluster_count", 0):
            run("copy_move_overlay", "copy_move_overlay.png", "Overlay copy-move ORB", "copy_move_orb", "manipulacao_local",
                "Caixas e vetores correspondem aos clusters de translação sinalizados pelo detector ORB.",
                lambda p: _copy_move_overlay(media, cm, p),
                "Texturas repetitivas podem produzir falsos positivos.")
        fc = methods.get("face_context_consistency") or {}
        if fc.get("faces_analyzed", 0):
            run("face_context_overlay", "face_context_overlay.png", "Face versus contexto", "face_context_consistency", "deepfake",
                "Região facial e vizinhança usadas na comparação de ruído e nitidez.",
                lambda p: _face_context_overlay(media, fc, p),
                "Iluminação, maquiagem e profundidade de campo podem criar discrepâncias semelhantes.")
        sf = methods.get("synthetic_feature_bank") or {}
        if sf.get("features"):
            run("synthetic_feature_profile", "synthetic_feature_profile.png", "Perfil de características sintéticas", "synthetic_feature_bank", "deepfake",
                "Painéis descritivos de wavelet, FFT, correlações RGB e textura/HOG. Cada painel possui escala própria.",
                lambda p: _synthetic_feature_profile(sf, p),
                "O gráfico descreve features; não é probabilidade de geração por IA.")
        if reference_path is not None and Path(reference_path).exists():
            ref_result = methods.get("reference_image_difference") or {}
            run("reference_difference", "reference_difference.png", "Diferença com referência", "reference_image_difference", "referencia",
                "Mapa de diferença absoluta em relação ao arquivo de referência informado.",
                lambda p: _reference_difference(media, Path(reference_path), p, ref_result),
                "Só é forte quando a referência é correspondente e sua proveniência é confiável.")
    else:
        mad, flow, frames = _video_series(media)
        if mad.size:
            run("video_transition_timeline", "video_transition_timeline.png", "Timeline de transições", "video_transition_anomalies", "video",
                "MAD frame a frame com marcação de transições abruptas e quase-duplicações.",
                lambda p: _video_transition_chart(mad, methods, p),
                "Cortes legítimos, flashes e mudanças de cena também podem ser sinalizados.")
        if flow.size:
            run("video_motion_timeline", "video_motion_timeline.png", "Timeline de movimento", "video_motion_discontinuities", "video",
                "Magnitude média do fluxo óptico ao longo das transições.",
                lambda p: _video_motion_chart(flow, methods, p),
                "Movimento rápido de câmera é uma causa alternativa comum.")
        target = media_dir / "video_keyframes.png"
        try:
            _video_keyframes(frames, methods, target)
            if target.exists():
                items.append(_artifact(root, target, "video_keyframes", "Frames-chave sinalizados", "video_transition_anomalies", "video",
                                       "Quadros correspondentes a eventos sinalizados pelos módulos temporais.",
                                       "Frames-chave são material de revisão visual, não uma conclusão automática."))
        except Exception as exc:
            errors.append({"id": "video_keyframes", "error": repr(exc)})

    return {
        "status": "success" if items else "no_artifacts",
        "media": media.name,
        "artifact_count": len(items),
        "items": items,
        "errors": errors,
        "warning": "Artefatos visuais são derivados para inspeção e documentação; não aumentam por si só o peso probatório do método que os originou.",
    }
