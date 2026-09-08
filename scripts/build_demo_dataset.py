from __future__ import annotations
import json, shutil
from pathlib import Path

import mf_lab  # activates Windows/OpenCV Unicode compatibility guards
import cv2, numpy as np
from skimage import data
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dataset'/'demo'
FIX=ROOT/'dataset'/'fixtures'

def save_rgb(path,arr,quality=95):
    path.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(arr.astype(np.uint8)).save(path,quality=quality)

def _write_png_unicode(path: Path, arr: np.ndarray):
    ok, buf = cv2.imencode('.png', arr)
    if not ok: raise RuntimeError(f'could not encode {path}')
    buf.tofile(path)

def _make_face_replacement(base_rgb: np.ndarray, donor_path: Path):
    base_bgr=cv2.cvtColor(base_rgb,cv2.COLOR_RGB2BGR)
    donor=cv2.imdecode(np.fromfile(donor_path,dtype=np.uint8),cv2.IMREAD_COLOR)
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    fb=cascade.detectMultiScale(cv2.cvtColor(base_bgr,cv2.COLOR_BGR2GRAY),1.1,5,minSize=(50,50))
    fd=cascade.detectMultiScale(cv2.cvtColor(donor,cv2.COLOR_BGR2GRAY),1.1,5,minSize=(30,30))
    if len(fb)==0 or len(fd)==0: raise RuntimeError('face fixture generation requires detectable faces')
    x,y,w,h=[int(v) for v in max(fb,key=lambda z:z[2]*z[3])]
    dx,dy,dw,dh=[int(v) for v in max(fd,key=lambda z:z[2]*z[3])]
    face=cv2.resize(donor[dy:dy+dh,dx:dx+dw],(w,h),interpolation=cv2.INTER_CUBIC)
    mask=np.zeros((h,w),np.uint8); cv2.ellipse(mask,(w//2,h//2),(int(w*.45),int(h*.48)),0,0,360,255,-1)
    blend=cv2.seamlessClone(face,base_bgr,mask,(x+w//2,y+h//2),cv2.NORMAL_CLONE)
    fullmask=np.zeros(base_bgr.shape[:2],np.uint8); fullmask[y:y+h,x:x+w]=mask
    return cv2.cvtColor(blend,cv2.COLOR_BGR2RGB), fullmask, [x,y,w,h]

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT/'images').mkdir(parents=True); (OUT/'videos').mkdir(parents=True); (OUT/'masks').mkdir(parents=True)
    a=data.astronaut(); c=data.coffee(); c=cv2.resize(c,(a.shape[1],a.shape[0]))
    save_rgb(OUT/'images'/'img_001_pristine.jpg',a,95)
    cm=a.copy(); patch=cm[90:190,70:170].copy(); cm[330:430,300:400]=patch; mask=np.zeros(a.shape[:2],np.uint8); mask[330:430,300:400]=255
    save_rgb(OUT/'images'/'img_002_copy_move.jpg',cm,92); _write_png_unicode(OUT/'masks'/'img_002_copy_move_mask.png',mask)
    sp=a.copy(); donor=c[150:280,170:330]; donor=cv2.GaussianBlur(donor,(3,3),0); sp[260:390,40:200]=donor; mask2=np.zeros(a.shape[:2],np.uint8); mask2[260:390,40:200]=255
    save_rgb(OUT/'images'/'img_003_splice.jpg',sp,90); _write_png_unicode(OUT/'masks'/'img_003_splice_mask.png',mask2)
    tmp=OUT/'images'/'_tmp.jpg'; save_rgb(tmp,a,70); Image.open(tmp).save(OUT/'images'/'img_004_double_jpeg.jpg',quality=92); tmp.unlink()
    h,w=a.shape[:2]; M=cv2.getRotationMatrix2D((w/2,h/2),3.2,1.08); rs=cv2.warpAffine(a,M,(w,h),borderMode=cv2.BORDER_REFLECT)
    save_rgb(OUT/'images'/'img_005_resampled.jpg',rs,94)
    bgr=cv2.cvtColor(a,cv2.COLOR_RGB2BGR); mk=np.zeros((h,w),np.uint8); cv2.circle(mk,(260,250),35,255,-1); inp=cv2.inpaint(bgr,mk,5,cv2.INPAINT_TELEA)
    save_rgb(OUT/'images'/'img_006_inpainted.jpg',cv2.cvtColor(inp,cv2.COLOR_BGR2RGB),93); _write_png_unicode(OUT/'masks'/'img_006_inpainted_mask.png',mk)

    face_rgb, face_mask, face_bbox = _make_face_replacement(a, FIX/'face_donor_ai.png')
    save_rgb(OUT/'images'/'img_007_deepfake_face.jpg',face_rgb,94)
    _write_png_unicode(OUT/'masks'/'img_007_deepfake_face_mask.png',face_mask)
    with Image.open(FIX/'ai_generated_fixture.png') as ai_src:
        ai_src.convert('RGB').resize((512,512),Image.Resampling.LANCZOS).save(OUT/'images'/'img_008_ai_generated.png')

    frames=[]
    for i in range(72):
        fr=a.copy(); x=20+(i*5)%400; cv2.circle(fr,(x,460),18,(255,255,255),-1); frames.append(cv2.cvtColor(fr,cv2.COLOR_RGB2BGR))
    def write_video(name, seq):
        p=OUT/'videos'/name; vw=cv2.VideoWriter(str(p),cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
        for fr in seq: vw.write(fr)
        vw.release()
    write_video('vid_001_pristine.mp4',frames)
    dup=frames[:36]+[frames[35]]*5+frames[36:]; write_video('vid_002_duplicated_frames.mp4',dup)
    deleted=frames[:30]+frames[40:]; write_video('vid_003_deleted_segment.mp4',deleted)
    overlay=[]
    for i,fr in enumerate(frames):
        f=fr.copy()
        if 25<=i<50: cv2.rectangle(f,(330,60),(500,150),(0,0,0),-1); cv2.putText(f,'EDIT',(350,120),cv2.FONT_HERSHEY_SIMPLEX,1.5,(255,255,255),3)
        overlay.append(f)
    write_video('vid_004_overlay_edit.mp4',overlay)

    gt={
      'images':{
       'img_001_pristine.jpg':{'label':'pristine'},
       'img_002_copy_move.jpg':{'label':'manipulated','method':'copy_move','mask':'../masks/img_002_copy_move_mask.png','source_bbox':[70,90,170,190],'destination_bbox':[300,330,400,430],'expected_translation_px':[230,240]},
       'img_003_splice.jpg':{'label':'manipulated','method':'splice','mask':'../masks/img_003_splice_mask.png','reference':'img_001_pristine.jpg','expected_bbox_xywh':[40,260,160,130]},
       'img_004_double_jpeg.jpg':{'label':'processed','method':'double_jpeg'},
       'img_005_resampled.jpg':{'label':'processed','method':'resampling'},
       'img_006_inpainted.jpg':{'label':'manipulated','method':'classical_inpainting','mask':'../masks/img_006_inpainted_mask.png','reference':'img_001_pristine.jpg','expected_bbox_xywh':[225,215,71,71]},
       'img_007_deepfake_face.jpg':{'label':'manipulated','method':'synthetic_face_replacement','mask':'../masks/img_007_deepfake_face_mask.png','reference':'img_001_pristine.jpg','face_bbox_xywh':face_bbox,'source':'AI-generated donor face blended only into face region','claim_scope':'controlled face-replacement fixture; not a benchmark DeepFaceLab/FaceSwap sample'},
       'img_008_ai_generated.png':{'label':'synthetic','method':'fully_ai_generated','source':'OpenAI-generated natural-scene fixture','source_fixture':'dataset/fixtures/ai_generated_fixture.png','claim_scope':'fully AI-generated pixels; controlled regression fixture only; not a population-valid benchmark sample'}},
      'videos':{
       'vid_001_pristine.mp4':{'label':'pristine'},
       'vid_002_duplicated_frames.mp4':{'label':'manipulated','method':'frame_duplication','expected_duplicate_transitions':[36,37,38,39,40]},
       'vid_003_deleted_segment.mp4':{'label':'manipulated','method':'segment_deletion_then_reencode','deleted_source_frames':[30,31,32,33,34,35,36,37,38,39],'reference':'vid_001_pristine.mp4','expected_questioned_transition_index':30,'expected_reference_jump':[29,40]},
       'vid_004_overlay_edit.mp4':{'label':'manipulated','method':'overlay_then_reencode','overlay_frame_range':[25,49],'expected_abrupt_transitions':[25,50]}},
      'note':'Controlled educational ground truth. It validates pipeline mechanics and regression behavior only, not real-world error rates or forensic validity. Reference-assisted checks require a trustworthy corresponding source file.'}
    (OUT/'ground_truth.json').write_text(json.dumps(gt,indent=2,ensure_ascii=False),encoding='utf-8')
    print(OUT)
if __name__=='__main__': main()
