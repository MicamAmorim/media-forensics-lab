from __future__ import annotations
import json
from pathlib import Path
from mf_lab.utils.io import run


def frame_timing(path: str | Path) -> dict:
    r=run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
           "frame=best_effort_timestamp_time,pkt_duration_time,pict_type,key_frame","-of","json",str(path)])
    if r["returncode"]: return {"error":r["stderr"]}
    frames=json.loads(r["stdout"]).get("frames",[])
    ts=[]
    for f in frames:
        try: ts.append(float(f.get("best_effort_timestamp_time")))
        except (TypeError,ValueError): pass
    gaps=[]
    if len(ts)>2:
        dt=[b-a for a,b in zip(ts,ts[1:])]
        med=sorted(dt)[len(dt)//2]
        gaps=[{"index":i,"delta":d} for i,d in enumerate(dt) if med>0 and d>1.8*med]
    return {"frame_count":len(frames),"timestamp_count":len(ts),"large_gaps":gaps,
            "i_frames":sum(1 for f in frames if f.get("pict_type")=="I")}


def frame_hash_duplicates(path: str | Path, mad_threshold: float = 0.05) -> dict:
    import cv2, numpy as np
    cap=cv2.VideoCapture(str(path)); frames=[]
    while True:
        ok,fr=cap.read()
        if not ok: break
        sm=cv2.resize(cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY),(64,64),interpolation=cv2.INTER_AREA)
        frames.append(sm.astype(np.float32))
    cap.release()
    dup=[]; distances=[]
    for i in range(1,len(frames)):
        mad=float(np.mean(np.abs(frames[i]-frames[i-1]))); distances.append(mad)
        if mad <= mad_threshold: dup.append(i)
    return {"frame_count":len(frames),"adjacent_near_duplicates":dup,"duplicate_count":len(dup),
            "mad_threshold":mad_threshold,"median_adjacent_mad":float(np.median(distances)) if distances else None}


def frame_transition_anomalies(path: str | Path, absolute_threshold: float = 0.01, robust_sigma: float = 8.0) -> dict:
    """Screen for abrupt frame-to-frame visual transitions.

    Frames are reduced to 64x64 grayscale and normalized to [0, 1].  A
    transition is flagged only when it exceeds both an absolute MAD threshold
    and a robust median/MAD-derived threshold. This is useful for abrupt
    overlays/cuts but is not a detector of every kind of video edit.
    """
    import cv2, numpy as np

    cap = cv2.VideoCapture(str(path))
    distances = []
    previous = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.resize(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            (64, 64),
            interpolation=cv2.INTER_AREA,
        ).astype(np.float32) / 255.0
        if previous is not None:
            distances.append(float(np.mean(np.abs(gray - previous))))
        previous = gray
    cap.release()

    if not distances:
        return {
            "frame_count": 0 if previous is None else 1,
            "transition_count": 0,
            "anomalous_transitions": [],
            "status": "screening_only",
        }

    arr = np.asarray(distances, dtype=np.float64)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    robust_threshold = median + robust_sigma * 1.4826 * mad
    threshold = max(float(absolute_threshold), float(robust_threshold))
    anomalies = [
        {"index": int(i + 1), "mean_abs_difference": float(v)}
        for i, v in enumerate(arr)
        if v >= threshold
    ]
    return {
        "frame_count": int(len(arr) + 1),
        "transition_count": int(len(arr)),
        "anomalous_transitions": anomalies,
        "anomaly_count": len(anomalies),
        "median_transition_mad": median,
        "robust_mad": mad,
        "threshold": threshold,
        "absolute_threshold": float(absolute_threshold),
        "robust_sigma": float(robust_sigma),
        "status": "screening_only",
        "warning": "Abrupt-transition screening can detect cuts/overlays but cannot establish manipulation by itself and may miss edits followed by smooth re-encoding.",
    }


def motion_discontinuity_screen(path: str | Path, robust_z_threshold: float = 2.0) -> dict:
    """Optical-flow discontinuity screening for abrupt content jumps.

    This can flag a cut/skip even when timestamps were repaired by re-encoding.
    It remains a screening heuristic: fast camera motion, flashes and hard cuts
    can produce similar outliers.
    """
    import cv2, numpy as np

    cap = cv2.VideoCapture(str(path))
    prev = None
    means = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (128, 128), interpolation=cv2.INTER_AREA)
        if prev is not None:
            flow = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 3, 21, 3, 5, 1.2, 0)
            mag = np.linalg.norm(flow, axis=2)
            means.append(float(np.mean(mag)))
        prev = gray
    cap.release()

    if not means:
        return {"status": "screening_only", "frame_count": 0 if prev is None else 1, "anomaly_count": 0, "anomalies": []}
    arr = np.asarray(means, dtype=np.float64)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    scale = 1.4826 * mad + 1e-12
    z = (arr - median) / scale
    anomalies = [
        {"index": int(i + 1), "mean_flow": float(arr[i]), "robust_z": float(z[i])}
        for i in range(len(arr)) if z[i] >= robust_z_threshold
    ]
    return {
        "status": "screening_only",
        "frame_count": int(len(arr) + 1),
        "transition_count": int(len(arr)),
        "median_mean_flow": median,
        "robust_mad": mad,
        "robust_z_threshold": float(robust_z_threshold),
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "warning": "Optical-flow discontinuities are non-specific. Fast motion, hard cuts and lighting changes may also trigger them; confirm with sequence/context review or a reference video when available.",
    }
