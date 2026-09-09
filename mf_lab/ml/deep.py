from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import yaml

from mf_lab.utils.io import cv_imread

DEEP_SCHEMA = "MFLAB-DEEP-MODEL-1.0"


def _load_config(path: str | Path) -> dict:
    p=Path(path); text=p.read_text(encoding="utf-8")
    data=json.loads(text) if p.suffix.lower()==".json" else yaml.safe_load(text)
    if not isinstance(data,dict): raise ValueError("deep model config must be an object")
    return data


def _largest_face_crop(rgb: np.ndarray) -> np.ndarray:
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    faces=cascade.detectMultiScale(gray,1.1,5,minSize=(48,48)) if not cascade.empty() else []
    if not len(faces): return rgb
    x,y,w,h=max(faces,key=lambda z:z[2]*z[3]); pad=int(round(.15*max(w,h)))
    return rgb[max(0,y-pad):min(rgb.shape[0],y+h+pad),max(0,x-pad):min(rgb.shape[1],x+w+pad)]


def predict_deep_config(image_path: str | Path, config_path: str | Path) -> dict:
    """Run an explicitly configured timm/PyTorch detector; no weights are bundled."""
    cfg=_load_config(config_path)
    try:
        import torch
        import timm
    except Exception as exc:
        raise RuntimeError("deep model support requires `pip install -e .[deep]`") from exc
    checkpoint=Path(config_path).parent/str(cfg.get("checkpoint",""))
    if not checkpoint.is_file(): checkpoint=Path(str(cfg.get("checkpoint","")))
    if not checkpoint.is_file(): raise FileNotFoundError(f"deep checkpoint not found: {cfg.get('checkpoint')}")
    architecture=str(cfg.get("architecture","resnet18")); size=int(cfg.get("image_size",224))
    model=timm.create_model(architecture,pretrained=False,num_classes=2)
    state=torch.load(checkpoint,map_location="cpu")
    if isinstance(state,dict) and "state_dict" in state: state=state["state_dict"]
    if not isinstance(state,dict): raise ValueError("checkpoint does not contain a state dict")
    model.load_state_dict({str(k).removeprefix("module."):v for k,v in state.items()},strict=True); model.eval()
    bgr=cv_imread(image_path,cv2.IMREAD_COLOR)
    if bgr is None: raise ValueError(f"unreadable image: {image_path}")
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    if bool(cfg.get("face_only")): rgb=_largest_face_crop(rgb)
    rgb=cv2.resize(rgb,(size,size),interpolation=cv2.INTER_AREA).astype(np.float32)/255.0
    mean=np.asarray(cfg.get("mean",[.485,.456,.406]),dtype=np.float32).reshape(1,1,3)
    std=np.asarray(cfg.get("std",[.229,.224,.225]),dtype=np.float32).reshape(1,1,3)
    x=torch.from_numpy(((rgb-mean)/std).transpose(2,0,1)).unsqueeze(0)
    with torch.no_grad(): logits=model(x).float().cpu().numpy()[0]
    temperature=float(cfg.get("temperature",1.0) or 1.0); temperature=temperature if temperature>0 else 1.0
    z=logits/temperature; z=z-z.max(); probs=np.exp(z)/np.exp(z).sum(); score=float(probs[1])
    calibrated=bool(cfg.get("calibrated")) and "temperature" in cfg
    return {"status":"success","schema":DEEP_SCHEMA,"model":cfg.get("name") or Path(config_path).stem,"model_kind":"deep",
            "architecture":architecture,"task":cfg.get("task","full_synthetic"),"face_only":bool(cfg.get("face_only")),
            "label":"synthetic" if score>=.5 else "real","score":score,"probability_synthetic":score if calibrated else None,
            "calibrated":calibrated,"temperature":temperature if calibrated else None,
            "scientifically_validated":bool(cfg.get("scientifically_validated")),"validation":cfg.get("validation_report"),
            "training_generators":cfg.get("training_generators",[]),"training_families":cfg.get("training_families",[]),
            "warning":"Deep-network confidence is not a forensic probability; calibration and independent scientific validation are separate requirements."}
