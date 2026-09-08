from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from mf_lab.analysis.reference import reference_image_difference, reference_video_sequence_alignment
from mf_lab.analysis.video import motion_discontinuity_screen
from mf_lab.pipeline import analyze_file
from mf_lab.utils.io import write_json


def _check(name: str, passed: bool, **details) -> dict:
    return {"check": name, "status": "pass" if passed else "fail", **details}


def _distance(a, b) -> float | None:
    if a is None or b is None or len(a) != len(b): return None
    return float(math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b))))


def _bbox_iou_xywh(a, b) -> float:
    if not a or not b: return 0.0
    ax,ay,aw,ah=[float(v) for v in a]; bx,by,bw,bh=[float(v) for v in b]
    x1=max(ax,bx); y1=max(ay,by); x2=min(ax+aw,bx+bw); y2=min(ay+ah,by+bh)
    inter=max(0.0,x2-x1)*max(0.0,y2-y1)
    union=aw*ah+bw*bh-inter
    return float(inter/union) if union>0 else 0.0


def validate_demo(dataset_dir: str | Path | None = None, out_path: str | Path | None = None) -> dict:
    """Controlled regression validation against bundled ground truth.

    Some checks are reference-assisted by design. Passing this harness does not
    estimate population error rates or prove reference-free forensic validity.
    """
    root=Path(__file__).resolve().parents[1]
    dataset=Path(dataset_dir) if dataset_dir else root/'dataset'/'demo'
    gt=json.loads((dataset/'ground_truth.json').read_text(encoding='utf-8'))
    reports={}
    with tempfile.TemporaryDirectory(prefix='mflab-validation-') as tmp:
        tmp_path=Path(tmp)
        for kind,subdir in [('images','images'),('videos','videos')]:
            for name,meta in gt.get(kind,{}).items():
                ref=meta.get('reference')
                ref_path=(dataset/subdir/ref) if ref else None
                reports[name]=analyze_file(dataset/subdir/name,tmp_path,profile='full',reference_path=ref_path)

    checks=[]
    p=reports['img_001_pristine.jpg']['methods']
    checks.append(_check('pristine_image_not_deepfake_escalated',p.get('deepfake_protocol',{}).get('triage_assessment')!='needs_expert_review',observed=p.get('deepfake_protocol',{}).get('triage_assessment')))
    checks.append(_check('pristine_image_no_copy_move_cluster',int(p.get('copy_move_orb',{}).get('suspicious_cluster_count',0) or 0)==0,observed=p.get('copy_move_orb',{}).get('suspicious_cluster_count')))

    cmgt=gt['images']['img_002_copy_move.jpg']; cm=reports['img_002_copy_move.jpg']['methods']['copy_move_orb']
    err=_distance(cmgt['expected_translation_px'],cm.get('dominant_translation_px'))
    checks.append(_check('copy_move_detected',int(cm.get('suspicious_pairs',0) or 0)>=10 and int(cm.get('suspicious_cluster_count',0) or 0)>=1,suspicious_pairs=cm.get('suspicious_pairs')))
    checks.append(_check('copy_move_translation_matches_fixture',err is not None and err<=8.0,error_px=err,observed=cm.get('dominant_translation_px'),expected=cmgt['expected_translation_px']))

    spgt=gt['images']['img_003_splice.jpg']; sp=reports['img_003_splice.jpg']['methods'].get('reference_image_difference',{})
    spiou=_bbox_iou_xywh(sp.get('largest_component_bbox_xywh'),spgt['expected_bbox_xywh'])
    checks.append(_check('splice_reference_localization',sp.get('component_count',0)>=1 and spiou>=0.75,iou=spiou,observed=sp.get('largest_component_bbox_xywh'),expected=spgt['expected_bbox_xywh'],scope='reference-assisted'))

    pristine_dct=float(p.get('jpeg_dct',{}).get('score',0) or 0); double_dct=float(reports['img_004_double_jpeg.jpg']['methods'].get('jpeg_dct',{}).get('score',0) or 0)
    ratio=double_dct/(pristine_dct+1e-12)
    checks.append(_check('double_jpeg_dct_ranks_above_pristine',double_dct>pristine_dct+0.05 and ratio>=2.0,pristine_score=pristine_dct,double_jpeg_score=double_dct,ratio=ratio,scope='diagnostic ranking only'))

    pr=p.get('resampling',{}); rs=reports['img_005_resampled.jpg']['methods'].get('resampling',{})
    checks.append(_check('resampling_fixture_separates_from_pristine',pr.get('screening_flag') is False and rs.get('screening_flag') is True,pristine=pr.get('short_lag_persistence'),resampled=rs.get('short_lag_persistence'),scope='screening regression'))

    igt=gt['images']['img_006_inpainted.jpg']; ir=reports['img_006_inpainted.jpg']['methods'].get('reference_image_difference',{})
    iiou=_bbox_iou_xywh(ir.get('largest_component_bbox_xywh'),igt['expected_bbox_xywh'])
    checks.append(_check('inpainting_reference_localization',ir.get('component_count',0)>=1 and iiou>=0.45,iou=iiou,observed=ir.get('largest_component_bbox_xywh'),expected=igt['expected_bbox_xywh'],scope='reference-assisted'))

    dfg=gt['images']['img_007_deepfake_face.jpg']; dfm=reports['img_007_deepfake_face.jpg']['methods']
    face_flags=dfm.get('face_artifacts',{}).get('screening_flags',[])
    checks.append(_check('face_replacement_native_screening_flag',bool(face_flags),flags=face_flags,scope='uncalibrated screening'))
    dfr=dfm.get('reference_image_difference',{}); dfiou=_bbox_iou_xywh(dfr.get('largest_component_bbox_xywh'),dfg['face_bbox_xywh'])
    checks.append(_check('face_replacement_reference_localization',dfr.get('component_count',0)>=1 and dfiou>=0.50,iou=dfiou,observed=dfr.get('largest_component_bbox_xywh'),expected=dfg['face_bbox_xywh'],scope='reference-assisted'))

    ai=reports['img_008_ai_generated.png']['methods']; aip=ai.get('deepfake_protocol',{})
    ai_obs=aip.get('screening_observations',[]) or []
    synthetic_obs=[x for x in ai_obs if x.get('family')=='synthetic_texture']
    checks.append(_check('ai_generated_native_synthetic_texture_screen',bool(synthetic_obs),observations=synthetic_obs,scope='uncalibrated engineering screening; one bundled AI fixture is not population validation'))

    pv=reports['vid_001_pristine.mp4']['methods']
    checks.append(_check('pristine_video_no_duplicate_or_abrupt_transition_flag',int(pv.get('video_duplicates',{}).get('duplicate_count',0) or 0)==0 and int(pv.get('video_transition_anomalies',{}).get('anomaly_count',0) or 0)==0,duplicate_count=pv.get('video_duplicates',{}).get('duplicate_count'),abrupt_count=pv.get('video_transition_anomalies',{}).get('anomaly_count')))

    dgt=gt['videos']['vid_002_duplicated_frames.mp4']; dv=reports['vid_002_duplicated_frames.mp4']['methods'].get('video_duplicates',{})
    checks.append(_check('duplicated_frames_exact_fixture_positions',dv.get('adjacent_near_duplicates',[])==dgt['expected_duplicate_transitions'],observed=dv.get('adjacent_near_duplicates'),expected=dgt['expected_duplicate_transitions']))

    sgt=gt['videos']['vid_003_deleted_segment.mp4']; sm=reports['vid_003_deleted_segment.mp4']['methods']
    motion=sm.get('video_motion_discontinuities',{}); mids=[x.get('index') for x in motion.get('anomalies',[])]
    checks.append(_check('segment_deletion_motion_discontinuity',sgt['expected_questioned_transition_index'] in mids,observed=mids,expected=sgt['expected_questioned_transition_index'],scope='blind screening; non-specific'))
    align=sm.get('reference_video_alignment',{}); skips=align.get('skipped_segments',[])
    exact=any(x.get('questioned_transition_index')==sgt['expected_questioned_transition_index'] and [x.get('previous_reference_index'),x.get('next_reference_index')]==sgt['expected_reference_jump'] and x.get('skipped_reference_count')==10 for x in skips)
    checks.append(_check('segment_deletion_reference_alignment',exact,skipped_segments=skips,scope='reference-assisted'))

    ogt=gt['videos']['vid_004_overlay_edit.mp4']; ov=reports['vid_004_overlay_edit.mp4']['methods'].get('video_transition_anomalies',{})
    oi=[x.get('index') for x in ov.get('anomalous_transitions',[])]
    checks.append(_check('overlay_edit_abrupt_boundaries_detected',oi==ogt['expected_abrupt_transitions'],observed=oi,expected=ogt['expected_abrupt_transitions']))

    failed=[c for c in checks if c['status']=='fail']
    result={
      'schema_version':'0.4','dataset':str(dataset),'ground_truth_note':gt.get('note'),
      'scope':'controlled regression validation; several checks are explicitly reference-assisted; not population-level forensic validation',
      'checks':checks,
      'summary':{'required_checks':len(checks),'passed':len(checks)-len(failed),'failed':len(failed),'unsupported':0,'ready_for_demo_regression':len(failed)==0},
      'interpretation':'Passing means the bundled fixtures exercise the expected code paths. Reference-assisted checks require a trustworthy source/reference. Native face and motion rules are screening heuristics. C2PA marker presence is not cryptographic validation unless c2patool validates the manifest. This does not establish sensitivity, specificity, false-positive rate or courtroom validity.'
    }
    if out_path is not None: write_json(Path(out_path),result)
    return result
