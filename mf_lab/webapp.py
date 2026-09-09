from __future__ import annotations

import json
import mimetypes
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import yaml
from flask import Flask, abort, jsonify, render_template, request, send_file, send_from_directory
from werkzeug.utils import secure_filename

from mf_lab.pipeline import IMAGE_EXTS, PROFILES, analyze_case
from mf_lab.report.generator import generate_preliminary_report
from mf_lab.version import current_version


RUN_ROOT = Path(tempfile.gettempdir()) / "mflab-web-runs"
RUN_ROOT.mkdir(parents=True, exist_ok=True)
MAX_FILES = 50
MAX_CONTENT_LENGTH = 250 * 1024 * 1024


def _clean_old_runs(max_age_hours: int = 24) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600
    for p in RUN_ROOT.iterdir():
        try:
            if p.is_dir() and p.stat().st_mtime < cutoff:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass


def _unique_name(original_dir: Path, raw_name: str) -> str:
    safe = secure_filename(raw_name) or "arquivo"
    stem = Path(safe).stem or "arquivo"
    suffix = Path(safe).suffix.lower()
    candidate = f"{stem}{suffix}"
    n = 2
    while (original_dir / candidate).exists():
        candidate = f"{stem}_{n}{suffix}"
        n += 1
    return candidate


def _numeric(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _signal_counts(methods: dict) -> dict[str, int]:
    local = compression = resampling = sensor = synthetic = provenance = 0
    cm = methods.get("copy_move_orb") or {}
    local += int(_numeric(cm.get("suspicious_cluster_count"), 0) > 0)
    dct = methods.get("jpeg_dct") or {}
    compression += int(_numeric(dct.get("score"), 0) >= 0.10)
    ghost = methods.get("jpeg_ghost") or {}
    compression += int(bool(ghost.get("suspicious_qualities") or ghost.get("candidates")))
    rs = methods.get("resampling") or {}
    resampling += int(rs.get("screening_flag") is True)
    nm = methods.get("noise_map") or {}
    sensor += len(nm.get("screening_flags") or [])
    prnu = methods.get("prnu_screen") or {}
    sensor += len(prnu.get("screening_flags") or [])
    face = methods.get("face_artifacts") or {}
    synthetic += len(face.get("screening_flags") or [])
    context = methods.get("face_context_consistency") or {}
    synthetic += len(context.get("screening_flags") or [])
    spectral = methods.get("synthetic_spectral") or {}
    synthetic += len(spectral.get("screening_flags") or [])
    proto = methods.get("deepfake_protocol") or methods.get("video_deepfake_protocol") or {}
    synthetic += len(proto.get("screening_observations") or [])
    synthetic += len(proto.get("evidence_families") or [])
    c2pa = methods.get("c2pa") or {}
    provenance += int(bool(c2pa.get("manifest") or c2pa.get("has_manifest") or c2pa.get("markers_found")))
    return {
        "Manipulação local": local,
        "Compressão/JPEG": compression,
        "Reamostragem": resampling,
        "Ruído/sensor": sensor,
        "Sintético/deepfake": synthetic,
        "Proveniência": provenance,
    }


def _method_summary(name: str, result) -> dict:
    if not isinstance(result, dict):
        return {"name": name, "status": "ok", "summary": str(result)}
    if result.get("status") == "error":
        return {"name": name, "status": "error", "summary": result.get("error", "erro")}
    interesting_keys = (
        "score", "score_synthetic", "predicted_label", "screening_flag", "screening_flags",
        "suspicious_pairs", "suspicious_cluster_count", "dominant_translation_px", "duplicate_count",
        "adjacent_near_duplicates", "anomaly_count", "triage_assessment", "evidentiary_conclusion",
        "validated_external_models", "protocol_version", "cryptographically_validated", "markers_found",
        "feature_count", "convergence_level", "family_count", "validated", "calibrated",
        "bundle_validated", "validated_for_input", "validation_scope_status",
    )
    picked = {k: result.get(k) for k in interesting_keys if k in result}
    if not picked:
        for k, v in result.items():
            if isinstance(v, (str, int, float, bool)) and len(picked) < 4:
                picked[k] = v
    text = json.dumps(picked or {"status": "executado"}, ensure_ascii=False, default=str)
    return {"name": name, "status": "ok", "summary": text}


def _artifact_rows(run_id: str, report: dict) -> list[dict]:
    rows = []
    for item in (report.get("visual_artifacts") or {}).get("items") or []:
        rel = str(item.get("path") or "").replace("\\", "/")
        if rel.startswith("visuals/"):
            rel = rel[len("visuals/"):]
        if not rel:
            continue
        row = dict(item)
        row["url"] = f"/api/run/{run_id}/artifact/{rel}"
        rows.append(row)
    return rows


def _serialize_report(run_id: str, report: dict) -> dict:
    name = Path(report.get("file", "arquivo")).name
    methods = report.get("methods") or {}
    proto = methods.get("deepfake_protocol") or methods.get("video_deepfake_protocol") or {}
    triage = proto.get("triage_assessment", "não informado") if isinstance(proto, dict) else "não informado"
    conclusion = proto.get("evidentiary_conclusion", "inconclusivo") if isinstance(proto, dict) else "inconclusivo"
    machine_assessment = proto.get("machine_assessment", {}) if isinstance(proto, dict) else {}
    signal_counts = _signal_counts(methods)
    artifacts = _artifact_rows(run_id, report)
    return {
        "name": name,
        "sha256": report.get("sha256"),
        "size_bytes": report.get("size_bytes"),
        "analyzed_at": report.get("analyzed_at"),
        "profile": report.get("profile"),
        "triage_assessment": triage,
        "evidentiary_conclusion": conclusion,
        "machine_assessment": machine_assessment,
        "signal_counts": signal_counts,
        "signal_total": sum(signal_counts.values()),
        "preview_url": f"/api/run/{run_id}/media/{name}",
        "methods": [_method_summary(k, v) for k, v in methods.items()],
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifact_warning": (report.get("visual_artifacts") or {}).get("warning"),
    }


def _write_case_yaml(case_dir: Path, case_id: str) -> None:
    payload = {"case": {
        "id": case_id,
        "title": "Análise interativa de mídia digital",
        "process_number": "",
        "court": "",
        "expert": {"name": "[NOME DO PERITO]", "qualification": "[QUALIFICAÇÃO]"},
        "scope": "Triagem técnico-forense automatizada de arquivos de mídia, com preservação de hash, métodos de análise nativos do MFLab e ressalva de que sinais automatizados não constituem veredito isolado de autenticidade, manipulação ou geração sintética.",
        "questions": [
            "Há sinais técnicos que justifiquem revisão pericial aprofundada?",
            "Há sinais compatíveis com manipulação local ou mídia sintética?",
        ],
    }}
    (case_dir / "case.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def create_app() -> Flask:
    template_folder = Path(__file__).resolve().parent / "web" / "templates"
    static_folder = Path(__file__).resolve().parent / "web" / "static"
    app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    _clean_old_runs()

    @app.get("/")
    def index():
        return render_template("index.html", profiles=sorted(PROFILES), version=current_version())

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "app": "MFLab Interactive Report", "version": current_version()})

    @app.post("/api/analyze")
    def analyze():
        uploads = request.files.getlist("files")
        if not uploads or all(not f.filename for f in uploads):
            return jsonify({"error": "Selecione pelo menos uma imagem."}), 400
        if len(uploads) > MAX_FILES:
            return jsonify({"error": f"Máximo de {MAX_FILES} arquivos por execução."}), 400
        profile = request.form.get("profile", "full")
        if profile not in PROFILES:
            return jsonify({"error": "Perfil de análise inválido."}), 400
        run_id = "web-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
        case_dir = RUN_ROOT / run_id
        original = case_dir / "original"
        for sub in ("original", "working", "results", "logs", "final", "visuals"):
            (case_dir / sub).mkdir(parents=True, exist_ok=True)
        _write_case_yaml(case_dir, run_id)
        accepted, rejected = [], []
        for upload in uploads:
            if not upload.filename:
                continue
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in IMAGE_EXTS:
                rejected.append({"name": upload.filename, "reason": "formato não suportado nesta interface"})
                continue
            name = _unique_name(original, upload.filename)
            upload.save(original / name)
            accepted.append(name)
        if not accepted:
            shutil.rmtree(case_dir, ignore_errors=True)
            return jsonify({"error": "Nenhuma imagem suportada foi recebida.", "rejected": rejected}), 400
        reports = analyze_case(case_dir, profile=profile, run_veritas=False)
        if not reports:
            return jsonify({"error": "O pipeline não produziu relatórios.", "run_id": run_id}), 500
        docx_path = generate_preliminary_report(case_dir, "docx")
        md_path = generate_preliminary_report(case_dir, "md")
        serialized = [_serialize_report(run_id, r) for r in reports]
        return jsonify({
            "run_id": run_id,
            "profile": profile,
            "accepted": accepted,
            "rejected": rejected,
            "files": serialized,
            "summary": {
                "files": len(serialized),
                "screening_signals": sum(x["signal_total"] for x in serialized),
                "needs_review": sum(x["triage_assessment"] == "needs_expert_review" for x in serialized),
                "inconclusive": sum(str(x["evidentiary_conclusion"]).lower() in {"inconclusive", "inconclusivo"} for x in serialized),
                "visual_artifacts": sum(x["artifact_count"] for x in serialized),
            },
            "downloads": {
                "docx": f"/api/run/{run_id}/download/docx",
                "md": f"/api/run/{run_id}/download/md",
                "json": f"/api/run/{run_id}/download/json",
            },
            "generated": {"docx": Path(docx_path).name, "md": Path(md_path).name},
            "warning": "A classificação automática real/sintética é separada da conclusão pericial. Gráficos e imagens derivados também não representam, isoladamente, peso de evidência.",
        })

    def _case_or_404(run_id: str) -> Path:
        case_dir = RUN_ROOT / secure_filename(run_id)
        if not case_dir.is_dir() or case_dir.parent != RUN_ROOT:
            abort(404)
        return case_dir

    @app.get("/api/run/<run_id>/media/<path:filename>")
    def media(run_id: str, filename: str):
        case_dir = _case_or_404(run_id)
        return send_from_directory(case_dir / "original", secure_filename(Path(filename).name), conditional=True)

    @app.get("/api/run/<run_id>/artifact/<path:filename>")
    def artifact(run_id: str, filename: str):
        case_dir = _case_or_404(run_id)
        posix = PurePosixPath(filename)
        if posix.is_absolute() or ".." in posix.parts:
            abort(404)
        return send_from_directory(case_dir / "visuals", posix.as_posix(), conditional=True)

    @app.get("/api/run/<run_id>/download/<kind>")
    def download(run_id: str, kind: str):
        case_dir = _case_or_404(run_id)
        if kind == "json":
            path, mimetype = case_dir / "report.json", "application/json"
        elif kind == "docx":
            matches = sorted((case_dir / "final").glob("*_laudo_preliminar.docx"))
            path = matches[0] if matches else Path(generate_preliminary_report(case_dir, "docx"))
            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif kind == "md":
            matches = sorted((case_dir / "final").glob("*_laudo_preliminar.md"))
            path = matches[0] if matches else Path(generate_preliminary_report(case_dir, "md"))
            mimetype = "text/markdown; charset=utf-8"
        else:
            abort(404)
        if not path.exists():
            abort(404)
        guessed = mimetypes.guess_type(path.name)[0]
        return send_file(path, as_attachment=True, download_name=path.name, mimetype=guessed or mimetype)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "O conjunto enviado excede 250 MB."}), 413

    return app


def run_web(host: str = "127.0.0.1", port: int = 8765, debug: bool = False) -> None:
    create_app().run(host=host, port=port, debug=debug, use_reloader=debug)
