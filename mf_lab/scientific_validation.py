from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from mf_lab.analysis.deepfake import image_deepfake_protocol
from mf_lab.analysis.synthetic_features import synthetic_feature_bank
from mf_lab.ml.synthetic import load_bundle, predict_bundle, save_bundle, train_classical_bundle
from mf_lab.utils.io import cv_imread, write_json

BENCHMARK_SCHEMA="MFLAB-SCI-BENCH-1.0"
REQUIRED_COLUMNS={"path","label","split"}


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def _label(value) -> int:
    s=str(value).strip().lower()
    if s in {"1","fake","synthetic","deepfake","ai","generated"}: return 1
    if s in {"0","real","pristine","authentic"}: return 0
    raise ValueError(f"unsupported label: {value!r}")


def load_manifest(path: str | Path) -> list[dict]:
    manifest=Path(path).resolve()
    if not manifest.is_file(): raise FileNotFoundError(manifest)
    if manifest.suffix.lower()==".jsonl":
        rows=[json.loads(x) for x in manifest.read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        with manifest.open("r",encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f); missing=REQUIRED_COLUMNS-set(reader.fieldnames or [])
            if missing: raise ValueError(f"manifest missing columns: {sorted(missing)}")
            rows=list(reader)
    if not rows: raise ValueError("manifest is empty")
    normalized=[]; seen=set()
    for i,row in enumerate(rows,start=2):
        rel=str(row.get("path","")).strip()
        if not rel: raise ValueError(f"manifest row {i}: path is empty")
        p=Path(rel); p=p if p.is_absolute() else (manifest.parent/p).resolve(); key=str(p).lower()
        if key in seen: raise ValueError(f"manifest duplicate path: {p}")
        seen.add(key)
        if not p.is_file(): raise FileNotFoundError(f"manifest row {i}: {p}")
        y=_label(row.get("label"))
        normalized.append({**row,"resolved_path":str(p),"label_binary":y,
            "split":str(row.get("split") or "test").strip().lower(),
            "generator":str(row.get("generator") or ("real" if y==0 else "unknown")).strip(),
            "family":str(row.get("family") or ("camera" if y==0 else "unknown")).strip(),
            "postprocess":str(row.get("postprocess") or row.get("transform") or "original").strip(),
            "source_id":str(row.get("source_id") or p.stem).strip()})
    source_splits=defaultdict(set)
    for row in normalized: source_splits[row["source_id"]].add(row["split"])
    leaked={k:sorted(v) for k,v in source_splits.items() if len(v)>1}
    if leaked: raise ValueError(f"source_id leakage across splits: {list(leaked.items())[:8]}")
    return normalized


def _ece(y: np.ndarray,p: np.ndarray,bins=10) -> float:
    edges=np.linspace(0,1,bins+1); total=max(1,len(y)); value=0.0
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=(p>=lo)&(p<(hi if hi<1 else hi+1e-12))
        if np.any(m): value += float(m.sum()/total)*abs(float(y[m].mean())-float(p[m].mean()))
    return float(value)


def classification_metrics(y_true,y_pred,scores=None,probabilities=None) -> dict:
    y=np.asarray(y_true,dtype=int); pred=np.asarray(y_pred,dtype=int)
    tn,fp,fn,tp=[int(x) for x in confusion_matrix(y,pred,labels=[0,1]).ravel()]
    out={"n":int(len(y)),"tn":tn,"fp":fp,"fn":fn,"tp":tp,
         "accuracy":float(accuracy_score(y,pred)),"balanced_accuracy":float(balanced_accuracy_score(y,pred)),
         "precision":float(precision_score(y,pred,zero_division=0)),"recall_sensitivity":float(recall_score(y,pred,zero_division=0)),
         "specificity":float(tn/max(1,tn+fp)),"fpr":float(fp/max(1,fp+tn)),"fnr":float(fn/max(1,fn+tp)),
         "f1":float(f1_score(y,pred,zero_division=0))}
    if scores is not None:
        s=np.asarray(scores,dtype=float)
        if len(np.unique(y))==2 and np.isfinite(s).all() and len(np.unique(s))>1:
            out["roc_auc"]=float(roc_auc_score(y,s)); out["pr_auc"]=float(average_precision_score(y,s))
    if probabilities is not None:
        p=np.asarray(probabilities,dtype=float)
        if len(p)==len(y) and np.isfinite(p).all() and np.all((p>=0)&(p<=1)):
            out["brier_score"]=float(brier_score_loss(y,p)); out["ece_10bin"]=_ece(y,p)
    return out


def extract_feature_matrix(rows: list[dict],splits: set[str] | None=None):
    selected=[r for r in rows if splits is None or r["split"] in splits]; X=[]; y=[]; names=None; kept=[]
    for row in selected:
        bank=synthetic_feature_bank(row["resolved_path"])
        if names is None: names=list(bank["feature_names"])
        if list(bank["feature_names"])!=names: raise RuntimeError("feature schema changed within benchmark")
        X.append(bank["feature_values"]); y.append(row["label_binary"]); kept.append(row)
    if not X: raise ValueError("no rows selected from manifest")
    return np.asarray(X,float),np.asarray(y,int),names or [],kept


def train_manifest_model(manifest_path,out_path,*,algorithm="svm_rbf",calibration="sigmoid") -> dict:
    manifest=Path(manifest_path).resolve(); rows=load_manifest(manifest)
    X,y,names,kept=extract_feature_matrix(rows,{"train"})
    bundle=train_classical_bundle(X,y,names,algorithm=algorithm,calibration=calibration,metadata={
        "training_manifest_sha256":_sha256(manifest),"training_generators":sorted({r["generator"] for r in kept if r["label_binary"]==1}),
        "training_families":sorted({r["family"] for r in kept if r["label_binary"]==1}),"scientifically_validated":False,"validation_report":None})
    save_bundle(bundle,out_path)
    return {"model":str(out_path),"algorithm":algorithm,"calibration":calibration,"train_n":int(len(y)),"scientifically_validated":False}


def _records(bundle: dict,rows: list[dict]) -> list[dict]:
    out=[]
    for row in rows:
        rr=predict_bundle(bundle,synthetic_feature_bank(row["resolved_path"]),model_name=bundle.get("algorithm"))
        prob=rr.get("probability_synthetic"); score=rr.get("score")
        if score is None: score=prob if prob is not None else (1.0 if rr.get("label")=="synthetic" else 0.0)
        out.append({"path":row["path"],"truth":row["label_binary"],"pred":1 if rr.get("label")=="synthetic" else 0,
            "score":float(score),"probability":prob,"generator":row["generator"],"family":row["family"],"postprocess":row["postprocess"]})
    return out


def _metrics(records):
    probs=None if any(r.get("probability") is None for r in records) else [r["probability"] for r in records]
    return classification_metrics([r["truth"] for r in records],[r["pred"] for r in records],[r["score"] for r in records],probs)


def _group(records,field):
    groups=defaultdict(list)
    for row in records: groups[str(row.get(field,"unknown"))].append(row)
    result={}
    for key,items in sorted(groups.items()):
        if len({x["truth"] for x in items})<2:
            result[key]={"n":len(items),"positives":sum(x["truth"]==1 for x in items),"predicted_positive_rate":float(np.mean([x["pred"] for x in items]))}
        else: result[key]=_metrics(items)
    return result


def _cross_holdout(rows,field,algorithms,calibration,seed):
    values=sorted({r[field] for r in rows if r["label_binary"]==1 and r[field] not in {"unknown","real","camera"}}); result={}
    for held in values:
        train=[r for r in rows if r["split"]=="train" and not (r["label_binary"]==1 and r[field]==held)]
        test=[r for r in rows if (r["label_binary"]==1 and r[field]==held and r["split"] in {"test","holdout","benchmark"}) or (r["label_binary"]==0 and r["split"] in {"test","holdout","benchmark"})]
        if len({r["label_binary"] for r in train})<2 or len({r["label_binary"] for r in test})<2: continue
        X,y,names,_=extract_feature_matrix(train); per={}
        for algorithm in algorithms:
            try: bundle=train_classical_bundle(X,y,names,algorithm=algorithm,calibration=calibration,metadata={"scientifically_validated":False},random_state=seed)
            except RuntimeError as exc: per[algorithm]={"status":"unavailable","error":str(exc)}; continue
            per[algorithm]={"status":"success","metrics":_metrics(_records(bundle,test)),"test_n":len(test)}
        result[held]=per
    return result


def scientific_suite(manifest_path,out_path="validation/scientific/suite.json",model_dir=None,algorithms=None,calibration="sigmoid",random_state=1337) -> dict:
    manifest=Path(manifest_path).resolve(); rows=load_manifest(manifest); train=[r for r in rows if r["split"]=="train"]; test=[r for r in rows if r["split"] in {"test","benchmark","holdout"}]
    if len({r["label_binary"] for r in train})<2 or len({r["label_binary"] for r in test})<2: raise ValueError("train and test/holdout must each contain real and synthetic samples")
    algorithms=algorithms or ["logistic","svm_rbf","extra_trees","xgboost"]; X,y,names,kept=extract_feature_matrix(train); models={}; exported=[]
    for algorithm in algorithms:
        try: bundle=train_classical_bundle(X,y,names,algorithm=algorithm,calibration=calibration,metadata={"training_manifest_sha256":_sha256(manifest),"training_generators":sorted({r["generator"] for r in kept if r["label_binary"]==1}),"training_families":sorted({r["family"] for r in kept if r["label_binary"]==1}),"scientifically_validated":False,"validation_report":str(out_path)},random_state=random_state)
        except RuntimeError as exc: models[algorithm]={"status":"unavailable","error":str(exc)}; continue
        rec=_records(bundle,test); models[algorithm]={"status":"success","overall":_metrics(rec),"by_generator":_group(rec,"generator"),"by_family":_group(rec,"family"),"by_postprocess":_group(rec,"postprocess")}
        if model_dir is not None:
            target=Path(model_dir)/f"synthetic_{algorithm}.joblib"; save_bundle(bundle,target); exported.append(str(target))
    successful={k:v for k,v in models.items() if v.get("status")=="success"}; selected=max(successful,key=lambda k:(successful[k]["overall"].get("balanced_accuracy",0),successful[k]["overall"].get("roc_auc",-1))) if successful else None
    report={"schema":BENCHMARK_SCHEMA,"protocol":"MFLAB-SCI-SYNTH-0.2","manifest":str(manifest),"manifest_sha256":_sha256(manifest),"sample_count":len(rows),"train_count":len(train),"test_count":len(test),"feature_count":len(names),"models":models,"selected_model_by_balanced_accuracy":selected,"leave_one_generator_out":_cross_holdout(rows,"generator",[a for a in algorithms if a!="xgboost"],calibration,random_state),"leave_one_family_out":_cross_holdout(rows,"family",[a for a in algorithms if a!="xgboost"],calibration,random_state),"exported_model_bundles":exported,"scientifically_validated":False,"interpretation":"Level-2 metrics quantify only the declared independent dataset/splits. Review leakage, FPR/FNR, cross-generator/family, post-processing and calibration before any domain-validity claim."}
    write_json(out_path,report); return report


def benchmark_manifest(manifest_path,*,model_paths=None,out_path="validation/scientific/detectors.json",include_native=True) -> dict:
    rows=load_manifest(manifest_path); test=[r for r in rows if r["split"] in {"test","benchmark","holdout"}]
    if len({r["label_binary"] for r in test})<2: raise ValueError("benchmark requires real and synthetic test rows")
    results={}
    if include_native:
        rec=[]
        for row in test:
            proto=image_deepfake_protocol(row["resolved_path"]); obs=proto.get("screening_observations") or []
            positive=any(x.get("family") in {"synthetic_texture","face_region"} for x in obs)
            rec.append({"truth":row["label_binary"],"pred":int(positive),"score":float(positive),"probability":None,"generator":row["generator"],"family":row["family"],"postprocess":row["postprocess"]})
        results["native_screening_baseline"]={"overall":_metrics(rec),"by_generator":_group(rec,"generator"),"by_family":_group(rec,"family"),"by_postprocess":_group(rec,"postprocess")}
    for path in model_paths or []:
        p=Path(path)
        if p.suffix.lower()==".joblib":
            rec=_records(load_bundle(p),test)
        else:
            from mf_lab.ml.deep import predict_deep_config
            rec=[]
            for row in test:
                rr=predict_deep_config(row["resolved_path"],p); prob=rr.get("probability_synthetic"); score=rr.get("score",0.0)
                rec.append({"truth":row["label_binary"],"pred":1 if rr.get("label")=="synthetic" else 0,"score":float(score),"probability":prob,"generator":row["generator"],"family":row["family"],"postprocess":row["postprocess"]})
        results[p.name]={"overall":_metrics(rec),"by_generator":_group(rec,"generator"),"by_family":_group(rec,"family"),"by_postprocess":_group(rec,"postprocess")}
    report={"schema":BENCHMARK_SCHEMA,"test_rows":len(test),"detectors":results,"interpretation":"Scientific validation layer; separate from CI regression."}; write_json(out_path,report); return report


def make_robustness_manifest(manifest_path,out_dir,operations=None) -> Path:
    rows=load_manifest(manifest_path); out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); ops=operations or ["jpeg95","jpeg75","jpeg50","resize50","blur","screenshot_like"]; output=[]
    for row in rows:
        if row["split"] not in {"test","benchmark","holdout"}: continue
        bgr=cv_imread(row["resolved_path"],cv2.IMREAD_COLOR)
        if bgr is None: continue
        h,w=bgr.shape[:2]; base=Path(row["resolved_path"])
        for op in ops:
            img=bgr.copy()
            if op=="resize50": img=cv2.resize(cv2.resize(img,(max(8,w//2),max(8,h//2)),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
            elif op=="blur": img=cv2.GaussianBlur(img,(0,0),1.2)
            elif op=="screenshot_like": img=cv2.resize(cv2.resize(img,(max(8,int(w*.75)),max(8,int(h*.75))),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
            elif not op.startswith("jpeg"): raise ValueError(f"unknown robustness operation: {op}")
            target=out/f"{base.stem}__{op}.jpg"; quality=int(op.replace("jpeg","")) if op.startswith("jpeg") else (90 if op=="screenshot_like" else 95); cv2.imwrite(str(target),img,[cv2.IMWRITE_JPEG_QUALITY,quality])
            output.append({"path":str(target.resolve()),"label":row["label"],"split":"test","generator":row["generator"],"family":row["family"],"postprocess":op,"source_id":f"{row['source_id']}__{op}"})
    target=out/"robustness_manifest.csv"
    with target.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["path","label","split","generator","family","postprocess","source_id"]); w.writeheader(); w.writerows(output)
    return target


def write_manifest_template(path) -> Path:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    rows=[{"path":"data/real/real_0001.jpg","label":"real","split":"train","generator":"real","family":"camera","postprocess":"original","source_id":"real_0001"},{"path":"data/stylegan2/fake_0001.png","label":"synthetic","split":"train","generator":"StyleGAN2","family":"GAN","postprocess":"original","source_id":"sg2_0001"},{"path":"data/stylegan3/fake_1001.png","label":"synthetic","split":"test","generator":"StyleGAN3","family":"GAN","postprocess":"original","source_id":"sg3_1001"},{"path":"data/diffusion/fake_2001.png","label":"synthetic","split":"holdout","generator":"ExampleDiffusion","family":"diffusion","postprocess":"original","source_id":"diff_2001"}]
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return p
