from __future__ import annotations
import io, math
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageChops, ImageEnhance
from scipy.fft import dctn


def ela(path: str | Path, quality: int = 90) -> dict:
    """Error Level Analysis. Screening aid only; never conclusive by itself."""
    im = Image.open(path).convert("RGB")
    b = io.BytesIO(); im.save(b, "JPEG", quality=quality); b.seek(0)
    rec = Image.open(b).convert("RGB")
    diff = ImageChops.difference(im, rec)
    arr = np.asarray(diff, dtype=np.float32)
    return {"mean_abs_error": float(arr.mean()), "max_error": int(arr.max()), "quality": quality,
            "warning": "ELA is exploratory only and is not proof of manipulation."}


def noise_residual_stats(path: str | Path) -> dict:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None: raise ValueError("unreadable image")
    imgf = img.astype(np.float32) / 255.0
    den = cv2.GaussianBlur(imgf, (0,0), 1.0)
    r = imgf - den
    return {"mean": float(r.mean()), "std": float(r.std()), "mad": float(np.median(np.abs(r-np.median(r))))}


def jpeg_dct_periodicity(path: str | Path) -> dict:
    """Simple research/teaching heuristic for periodic gaps in DCT histograms.
    This is not a validated double-JPEG detector."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None: raise ValueError("unreadable image")
    h, w = img.shape; h -= h % 8; w -= w % 8; img = img[:h,:w].astype(np.float32)-128
    coeffs=[]
    for y in range(0,h,8):
        for x in range(0,w,8):
            c=dctn(img[y:y+8,x:x+8], type=2, norm='ortho'); coeffs.append(c[1,2])
    q=np.rint(np.asarray(coeffs)).astype(int)
    if q.size < 10: return {"score": 0.0, "n_blocks": int(q.size)}
    lo,hi=np.percentile(q,[2,98]).astype(int); bins=np.arange(lo,hi+2)
    hist,_=np.histogram(q,bins=bins)
    if len(hist)<5: return {"score":0.0,"n_blocks":int(q.size)}
    z=float(np.mean(hist==0)); alt=float(np.mean(np.abs(np.diff(hist))))/(float(np.mean(hist))+1e-9)
    score=min(1.0, 0.5*z + 0.05*alt)
    return {"score": score, "n_blocks": int(q.size), "zero_bin_fraction": z,
            "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use."}


def copy_move_orb(path: str | Path) -> dict:
    img=cv2.imread(str(path));
    if img is None: raise ValueError("unreadable image")
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    orb=cv2.ORB_create(nfeatures=2500)
    kp,des=orb.detectAndCompute(gray,None)
    if des is None or len(kp)<4: return {"keypoints":len(kp),"suspicious_pairs":0,"score":0.0}
    m=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True).match(des,des)
    pairs=[]
    for mt in m:
        if mt.queryIdx==mt.trainIdx: continue
        p1=np.array(kp[mt.queryIdx].pt); p2=np.array(kp[mt.trainIdx].pt)
        d=float(np.linalg.norm(p1-p2))
        if mt.distance<35 and d>40: pairs.append((mt.distance,d))
    score=min(1.0,len(pairs)/20.0)
    return {"keypoints":len(kp),"suspicious_pairs":len(pairs),"score":score,
            "warning":"Feature matching is a screening detector; repetitive textures can cause false positives."}
