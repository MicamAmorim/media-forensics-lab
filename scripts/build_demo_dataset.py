from __future__ import annotations
import json, shutil
from pathlib import Path
import cv2, numpy as np
from skimage import data
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dataset'/'demo'

def save_rgb(path,arr,quality=95):
    path.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(arr.astype(np.uint8)).save(path,quality=quality)

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT/'images').mkdir(parents=True); (OUT/'videos').mkdir(parents=True); (OUT/'masks').mkdir(parents=True)
    a=data.astronaut(); c=data.coffee(); c=cv2.resize(c,(a.shape[1],a.shape[0]))
    save_rgb(OUT/'images'/'img_001_pristine.jpg',a,95)
    # copy-move
    cm=a.copy(); patch=cm[90:190,70:170].copy(); cm[330:430,300:400]=patch; mask=np.zeros(a.shape[:2],np.uint8); mask[330:430,300:400]=255
    save_rgb(OUT/'images'/'img_002_copy_move.jpg',cm,92); cv2.imwrite(str(OUT/'masks'/'img_002_copy_move_mask.png'),mask)
    # splice
    sp=a.copy(); donor=c[150:280,170:330]; donor=cv2.GaussianBlur(donor,(3,3),0); sp[260:390,40:200]=donor; mask2=np.zeros(a.shape[:2],np.uint8); mask2[260:390,40:200]=255
    save_rgb(OUT/'images'/'img_003_splice.jpg',sp,90); cv2.imwrite(str(OUT/'masks'/'img_003_splice_mask.png'),mask2)
    # double jpeg
    tmp=OUT/'images'/'_tmp.jpg'; save_rgb(tmp,a,70); Image.open(tmp).save(OUT/'images'/'img_004_double_jpeg.jpg',quality=92); tmp.unlink()
    # resample rotate crop back
    h,w=a.shape[:2]; M=cv2.getRotationMatrix2D((w/2,h/2),3.2,1.08); rs=cv2.warpAffine(a,M,(w,h),borderMode=cv2.BORDER_REFLECT)
    save_rgb(OUT/'images'/'img_005_resampled.jpg',rs,94)
    # inpainting-like classic object removal
    bgr=cv2.cvtColor(a,cv2.COLOR_RGB2BGR); mk=np.zeros((h,w),np.uint8); cv2.circle(mk,(260,250),35,255,-1); inp=cv2.inpaint(bgr,mk,5,cv2.INPAINT_TELEA)
    save_rgb(OUT/'images'/'img_006_inpainted.jpg',cv2.cvtColor(inp,cv2.COLOR_BGR2RGB),93); cv2.imwrite(str(OUT/'masks'/'img_006_inpainted_mask.png'),mk)
    # video sequence
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
       'img_001_pristine.jpg':{'label':'pristine'},'img_002_copy_move.jpg':{'label':'manipulated','method':'copy_move','mask':'../masks/img_002_copy_move_mask.png','source_bbox':[70,90,170,190],'destination_bbox':[300,330,400,430],'expected_translation_px':[230,240]},
       'img_003_splice.jpg':{'label':'manipulated','method':'splice','mask':'../masks/img_003_splice_mask.png'},'img_004_double_jpeg.jpg':{'label':'processed','method':'double_jpeg'},
       'img_005_resampled.jpg':{'label':'processed','method':'resampling'},'img_006_inpainted.jpg':{'label':'manipulated','method':'classical_inpainting','mask':'../masks/img_006_inpainted_mask.png'}},
      'videos':{
       'vid_001_pristine.mp4':{'label':'pristine'},'vid_002_duplicated_frames.mp4':{'label':'manipulated','method':'frame_duplication','expected_duplicate_transitions':[36,37,38,39,40]},
       'vid_003_deleted_segment.mp4':{'label':'manipulated','method':'segment_deletion_then_reencode','deleted_source_frames':[30,31,32,33,34,35,36,37,38,39]},'vid_004_overlay_edit.mp4':{'label':'manipulated','method':'overlay_then_reencode','overlay_frame_range':[25,49],'expected_abrupt_transitions':[25,50]}},
      'note':'Controlled educational ground truth. It validates pipeline mechanics and regression behavior only, not real-world error rates or forensic validity.'}
    (OUT/'ground_truth.json').write_text(json.dumps(gt,indent=2,ensure_ascii=False),encoding='utf-8')
    print(OUT)
if __name__=='__main__': main()
