from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from mf_lab.pipeline import analyze_file
from mf_lab.utils.io import write_json

MEDIA_KINDS = {"images": "images", "videos": "videos"}


def _check(name: str, passed: bool, fixture: str, **details) -> dict:
    return {
        "check": name,
        "fixture": fixture,
        "status": "pass" if passed else "fail",
        **details,
    }


def _distance(a, b) -> float | None:
    if a is None or b is None or len(a) != len(b):
        return None
    return float(math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))))


def _bbox_iou_xywh(a, b) -> float:
    if not a or not b:
        return 0.0
    ax, ay, aw, ah = [float(v) for v in a]
    bx, by, bw, bh = [float(v) for v in b]
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


def _gt_contract(dataset: Path, gt: dict, checks: list[dict]) -> dict:
    """Validate the GT oracle itself and its one-to-one link to assertions.

    Every fixture must declare at least one ``required_check`` and every
    produced validation check must be declared by exactly one fixture. This
    makes new GT entries fail closed: adding a fixture without adding an
    explicit regression assertion cannot yield a green CI run.
    """
    project_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    declared: dict[str, list[str]] = {}

    for kind, subdir in MEDIA_KINDS.items():
        entries = gt.get(kind)
        if not isinstance(entries, dict) or not entries:
            errors.append(f"GT section '{kind}' must be a non-empty object")
            continue

        for name, meta in entries.items():
            if not isinstance(meta, dict):
                errors.append(f"{kind}/{name}: GT entry must be an object")
                continue

            media_path = dataset / subdir / name
            if not media_path.is_file():
                errors.append(f"{kind}/{name}: fixture file is missing: {media_path}")

            label = meta.get("label")
            if not isinstance(label, str) or not label.strip():
                errors.append(f"{kind}/{name}: non-empty label is required")
            elif label != "pristine" and not meta.get("method"):
                errors.append(f"{kind}/{name}: non-pristine fixture requires method")

            required = meta.get("required_checks")
            if not isinstance(required, list) or not required:
                errors.append(f"{kind}/{name}: required_checks must be a non-empty list")
                declared[name] = []
            else:
                normalized = [str(x) for x in required]
                if len(normalized) != len(set(normalized)):
                    errors.append(f"{kind}/{name}: required_checks contains duplicates")
                declared[name] = normalized

            reference = meta.get("reference")
            if reference:
                reference_path = dataset / subdir / str(reference)
                if not reference_path.is_file():
                    errors.append(
                        f"{kind}/{name}: reference file is missing: {reference_path}"
                    )

            mask = meta.get("mask")
            if mask:
                mask_path = dataset / subdir / str(mask)
                if not mask_path.is_file():
                    errors.append(f"{kind}/{name}: mask file is missing: {mask_path}")

            source_fixture = meta.get("source_fixture")
            if source_fixture:
                source_path = project_root / str(source_fixture)
                if not source_path.is_file():
                    errors.append(
                        f"{kind}/{name}: source_fixture is missing: {source_path}"
                    )

    produced_names = [str(c.get("check")) for c in checks]
    if len(produced_names) != len(set(produced_names)):
        errors.append("validation code produced duplicate check names")

    declared_pairs = [
        (fixture, check_name)
        for fixture, required in declared.items()
        for check_name in required
    ]
    declared_names = [name for _, name in declared_pairs]
    if len(declared_names) != len(set(declared_names)):
        errors.append("a required check name is declared by more than one GT fixture")

    declared_lookup = {check_name: fixture for fixture, check_name in declared_pairs}
    produced_lookup = {str(c.get("check")): c for c in checks}

    for check_name, fixture in declared_lookup.items():
        produced = produced_lookup.get(check_name)
        if produced is None:
            errors.append(f"GT requires check '{check_name}' but validation did not produce it")
        elif produced.get("fixture") != fixture:
            errors.append(
                f"check '{check_name}' belongs to '{produced.get('fixture')}', "
                f"but GT declares it for '{fixture}'"
            )

    for check_name, produced in produced_lookup.items():
        if check_name not in declared_lookup:
            errors.append(
                f"validation produced undeclared check '{check_name}' "
                f"for fixture '{produced.get('fixture')}'"
            )

    return {"errors": errors, "declared_checks": declared}


def _coverage_summary(gt: dict, checks: list[dict], contract: dict) -> tuple[dict, list[dict]]:
    check_index = {str(c.get("check")): c for c in checks}
    declared = contract.get("declared_checks", {})
    fixture_rows: list[dict] = []

    required_total = 0
    present_total = 0
    passed_total = 0
    fully_covered_fixtures = 0
    fully_passed_fixtures = 0

    for kind in MEDIA_KINDS:
        for fixture in (gt.get(kind) or {}):
            required = list(declared.get(fixture, []))
            required_total += len(required)
            present = [name for name in required if name in check_index]
            passed = [
                name
                for name in required
                if name in check_index
                and check_index[name].get("fixture") == fixture
                and check_index[name].get("status") == "pass"
            ]
            missing = [name for name in required if name not in check_index]
            failing = [
                name
                for name in required
                if name in check_index and check_index[name].get("status") != "pass"
            ]
            wrong_fixture = [
                name
                for name in required
                if name in check_index and check_index[name].get("fixture") != fixture
            ]

            present_total += len(present)
            passed_total += len(passed)
            fully_covered = bool(required) and not missing and not wrong_fixture
            fully_passed = fully_covered and len(passed) == len(required)
            if fully_covered:
                fully_covered_fixtures += 1
            if fully_passed:
                fully_passed_fixtures += 1

            fixture_rows.append(
                {
                    "fixture": fixture,
                    "required_checks": required,
                    "present_checks": present,
                    "passed_checks": passed,
                    "missing_checks": missing,
                    "failing_checks": failing,
                    "wrong_fixture_checks": wrong_fixture,
                    "coverage_complete": fully_covered,
                    "validated": fully_passed,
                }
            )

    fixture_count = len(fixture_rows)
    assertion_coverage = 100.0 if required_total == 0 else 100.0 * present_total / required_total
    pass_rate = 100.0 if required_total == 0 else 100.0 * passed_total / required_total
    fixture_coverage = 100.0 if fixture_count == 0 else 100.0 * fully_covered_fixtures / fixture_count
    fixture_pass_rate = 100.0 if fixture_count == 0 else 100.0 * fully_passed_fixtures / fixture_count

    summary = {
        "required_checks": required_total,
        "passed": passed_total,
        "failed": required_total - passed_total,
        "unsupported": 0,
        "gt_fixture_count": fixture_count,
        "gt_fixtures_covered": fully_covered_fixtures,
        "gt_fixtures_validated": fully_passed_fixtures,
        "gt_fixture_coverage_pct": round(fixture_coverage, 6),
        "gt_fixture_pass_rate_pct": round(fixture_pass_rate, 6),
        "gt_required_assertions": required_total,
        "gt_assertions_present": present_total,
        "gt_assertions_passed": passed_total,
        "gt_assertion_coverage_pct": round(assertion_coverage, 6),
        "gt_pass_rate_pct": round(pass_rate, 6),
        "gt_contract_errors": len(contract.get("errors", [])),
    }
    summary["ready_for_demo_regression"] = (
        required_total > 0
        and summary["gt_contract_errors"] == 0
        and summary["gt_fixture_coverage_pct"] == 100.0
        and summary["gt_fixture_pass_rate_pct"] == 100.0
        and summary["gt_assertion_coverage_pct"] == 100.0
        and summary["gt_pass_rate_pct"] == 100.0
        and summary["unsupported"] == 0
    )
    return summary, fixture_rows


def validate_demo(
    dataset_dir: str | Path | None = None,
    out_path: str | Path | None = None,
) -> dict:
    """Controlled regression validation against canonical bundled ground truth.

    The CI contract is intentionally strict: every fixture and every required
    assertion declared by ``ground_truth.json`` must be present and pass.
    Passing this harness still does not estimate population error rates or prove
    reference-free forensic validity.
    """
    root = Path(__file__).resolve().parents[1]
    dataset = Path(dataset_dir) if dataset_dir else root / "dataset" / "demo"
    gt = json.loads((dataset / "ground_truth.json").read_text(encoding="utf-8"))

    reports = {}
    with tempfile.TemporaryDirectory(prefix="mflab-validation-") as tmp:
        tmp_path = Path(tmp)
        for kind, subdir in MEDIA_KINDS.items():
            for name, meta in gt.get(kind, {}).items():
                ref = meta.get("reference")
                ref_path = dataset / subdir / ref if ref else None
                reports[name] = analyze_file(
                    dataset / subdir / name,
                    tmp_path,
                    profile="full",
                    reference_path=ref_path,
                )

    checks: list[dict] = []

    p = reports["img_001_pristine.jpg"]["methods"]
    checks.append(
        _check(
            "pristine_image_not_deepfake_escalated",
            p.get("deepfake_protocol", {}).get("triage_assessment")
            != "needs_expert_review",
            "img_001_pristine.jpg",
            observed=p.get("deepfake_protocol", {}).get("triage_assessment"),
        )
    )
    checks.append(
        _check(
            "pristine_image_no_copy_move_cluster",
            int(p.get("copy_move_orb", {}).get("suspicious_cluster_count", 0) or 0)
            == 0,
            "img_001_pristine.jpg",
            observed=p.get("copy_move_orb", {}).get("suspicious_cluster_count"),
        )
    )

    cmgt = gt["images"]["img_002_copy_move.jpg"]
    cm = reports["img_002_copy_move.jpg"]["methods"]["copy_move_orb"]
    err = _distance(cmgt["expected_translation_px"], cm.get("dominant_translation_px"))
    checks.append(
        _check(
            "copy_move_detected",
            int(cm.get("suspicious_pairs", 0) or 0) >= 10
            and int(cm.get("suspicious_cluster_count", 0) or 0) >= 1,
            "img_002_copy_move.jpg",
            suspicious_pairs=cm.get("suspicious_pairs"),
        )
    )
    checks.append(
        _check(
            "copy_move_translation_matches_fixture",
            err is not None and err <= 8.0,
            "img_002_copy_move.jpg",
            error_px=err,
            observed=cm.get("dominant_translation_px"),
            expected=cmgt["expected_translation_px"],
        )
    )

    spgt = gt["images"]["img_003_splice.jpg"]
    sp = reports["img_003_splice.jpg"]["methods"].get(
        "reference_image_difference", {}
    )
    spiou = _bbox_iou_xywh(
        sp.get("largest_component_bbox_xywh"), spgt["expected_bbox_xywh"]
    )
    checks.append(
        _check(
            "splice_reference_localization",
            sp.get("component_count", 0) >= 1 and spiou >= 0.75,
            "img_003_splice.jpg",
            iou=spiou,
            observed=sp.get("largest_component_bbox_xywh"),
            expected=spgt["expected_bbox_xywh"],
            scope="reference-assisted",
        )
    )

    pristine_dct = float(p.get("jpeg_dct", {}).get("score", 0) or 0)
    double_dct = float(
        reports["img_004_double_jpeg.jpg"]["methods"]
        .get("jpeg_dct", {})
        .get("score", 0)
        or 0
    )
    ratio = double_dct / (pristine_dct + 1e-12)
    checks.append(
        _check(
            "double_jpeg_dct_ranks_above_pristine",
            double_dct > pristine_dct + 0.05 and ratio >= 2.0,
            "img_004_double_jpeg.jpg",
            pristine_score=pristine_dct,
            double_jpeg_score=double_dct,
            ratio=ratio,
            scope="diagnostic ranking only",
        )
    )

    pr = p.get("resampling", {})
    rs = reports["img_005_resampled.jpg"]["methods"].get("resampling", {})
    checks.append(
        _check(
            "resampling_fixture_separates_from_pristine",
            pr.get("screening_flag") is False and rs.get("screening_flag") is True,
            "img_005_resampled.jpg",
            pristine=pr.get("short_lag_persistence"),
            resampled=rs.get("short_lag_persistence"),
            scope="screening regression",
        )
    )

    igt = gt["images"]["img_006_inpainted.jpg"]
    ir = reports["img_006_inpainted.jpg"]["methods"].get(
        "reference_image_difference", {}
    )
    iiou = _bbox_iou_xywh(
        ir.get("largest_component_bbox_xywh"), igt["expected_bbox_xywh"]
    )
    checks.append(
        _check(
            "inpainting_reference_localization",
            ir.get("component_count", 0) >= 1 and iiou >= 0.45,
            "img_006_inpainted.jpg",
            iou=iiou,
            observed=ir.get("largest_component_bbox_xywh"),
            expected=igt["expected_bbox_xywh"],
            scope="reference-assisted",
        )
    )

    dfg = gt["images"]["img_007_deepfake_face.jpg"]
    dfm = reports["img_007_deepfake_face.jpg"]["methods"]
    face_flags = dfm.get("face_artifacts", {}).get("screening_flags", [])
    checks.append(
        _check(
            "face_replacement_native_screening_flag",
            bool(face_flags),
            "img_007_deepfake_face.jpg",
            flags=face_flags,
            scope="uncalibrated screening",
        )
    )
    dfr = dfm.get("reference_image_difference", {})
    dfiou = _bbox_iou_xywh(
        dfr.get("largest_component_bbox_xywh"), dfg["face_bbox_xywh"]
    )
    checks.append(
        _check(
            "face_replacement_reference_localization",
            dfr.get("component_count", 0) >= 1 and dfiou >= 0.50,
            "img_007_deepfake_face.jpg",
            iou=dfiou,
            observed=dfr.get("largest_component_bbox_xywh"),
            expected=dfg["face_bbox_xywh"],
            scope="reference-assisted",
        )
    )

    ai = reports["img_008_ai_generated.png"]["methods"]
    aip = ai.get("deepfake_protocol", {})
    ai_obs = aip.get("screening_observations", []) or []
    synthetic_obs = [x for x in ai_obs if x.get("family") == "synthetic_texture"]
    checks.append(
        _check(
            "ai_generated_native_synthetic_texture_screen",
            bool(synthetic_obs),
            "img_008_ai_generated.png",
            observations=synthetic_obs,
            scope=(
                "uncalibrated engineering screening; one bundled AI fixture "
                "is not population validation"
            ),
        )
    )

    pv = reports["vid_001_pristine.mp4"]["methods"]
    checks.append(
        _check(
            "pristine_video_no_duplicate_or_abrupt_transition_flag",
            int(pv.get("video_duplicates", {}).get("duplicate_count", 0) or 0) == 0
            and int(
                pv.get("video_transition_anomalies", {}).get("anomaly_count", 0) or 0
            )
            == 0,
            "vid_001_pristine.mp4",
            duplicate_count=pv.get("video_duplicates", {}).get("duplicate_count"),
            abrupt_count=pv.get("video_transition_anomalies", {}).get(
                "anomaly_count"
            ),
        )
    )

    dgt = gt["videos"]["vid_002_duplicated_frames.mp4"]
    dv = reports["vid_002_duplicated_frames.mp4"]["methods"].get(
        "video_duplicates", {}
    )
    checks.append(
        _check(
            "duplicated_frames_exact_fixture_positions",
            dv.get("adjacent_near_duplicates", []) == dgt["expected_duplicate_transitions"],
            "vid_002_duplicated_frames.mp4",
            observed=dv.get("adjacent_near_duplicates"),
            expected=dgt["expected_duplicate_transitions"],
        )
    )

    sgt = gt["videos"]["vid_003_deleted_segment.mp4"]
    sm = reports["vid_003_deleted_segment.mp4"]["methods"]
    motion = sm.get("video_motion_discontinuities", {})
    mids = [x.get("index") for x in motion.get("anomalies", [])]
    checks.append(
        _check(
            "segment_deletion_motion_discontinuity",
            sgt["expected_questioned_transition_index"] in mids,
            "vid_003_deleted_segment.mp4",
            observed=mids,
            expected=sgt["expected_questioned_transition_index"],
            scope="blind screening; non-specific",
        )
    )
    align = sm.get("reference_video_alignment", {})
    skips = align.get("skipped_segments", [])
    exact = any(
        x.get("questioned_transition_index") == sgt["expected_questioned_transition_index"]
        and [x.get("previous_reference_index"), x.get("next_reference_index")]
        == sgt["expected_reference_jump"]
        and x.get("skipped_reference_count") == len(sgt["deleted_source_frames"])
        for x in skips
    )
    checks.append(
        _check(
            "segment_deletion_reference_alignment",
            exact,
            "vid_003_deleted_segment.mp4",
            skipped_segments=skips,
            scope="reference-assisted",
        )
    )

    ogt = gt["videos"]["vid_004_overlay_edit.mp4"]
    ov = reports["vid_004_overlay_edit.mp4"]["methods"].get(
        "video_transition_anomalies", {}
    )
    oi = [x.get("index") for x in ov.get("anomalous_transitions", [])]
    checks.append(
        _check(
            "overlay_edit_abrupt_boundaries_detected",
            oi == ogt["expected_abrupt_transitions"],
            "vid_004_overlay_edit.mp4",
            observed=oi,
            expected=ogt["expected_abrupt_transitions"],
        )
    )

    contract = _gt_contract(dataset, gt, checks)
    summary, fixture_validation = _coverage_summary(gt, checks, contract)

    result = {
        "schema_version": "0.5",
        "dataset": str(dataset),
        "ground_truth_note": gt.get("note"),
        "scope": (
            "controlled regression validation; several checks are explicitly "
            "reference-assisted; not population-level forensic validation"
        ),
        "gt_contract": contract,
        "fixture_validation": fixture_validation,
        "checks": checks,
        "summary": summary,
        "interpretation": (
            "A green GT gate means every fixture and every required assertion "
            "declared by the canonical ground_truth.json is present and passed. "
            "Reference-assisted checks require a trustworthy source/reference. "
            "Native face and motion rules remain screening heuristics. C2PA marker "
            "presence is not cryptographic validation unless c2patool validates the "
            "manifest. 100% GT regression is not sensitivity/specificity, a false-"
            "positive-rate estimate, or courtroom validity."
        ),
    }
    if out_path is not None:
        write_json(Path(out_path), result)
    return result
