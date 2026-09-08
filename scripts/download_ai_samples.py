"""Optional downloader for a SMALL licensed AI-vs-real subset.
Requires: pip install datasets
Default source: dragonintelligence/CIFAKE-image-dataset on Hugging Face.
The dataset is not bundled in the ZIP to keep it small and to preserve upstream licensing/attribution.
"""
from pathlib import Path
import argparse

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--n-per-class',type=int,default=12); a=ap.parse_args()
    from datasets import load_dataset
    ds=load_dataset('dragonintelligence/CIFAKE-image-dataset',split='test',streaming=True)
    out=Path(__file__).resolve().parents[1]/'dataset'/'ai_samples'; out.mkdir(parents=True,exist_ok=True)
    counts={0:0,1:0}
    for row in ds:
        lab=int(row['label'])
        if counts.get(lab,0)>=a.n_per_class: continue
        label='fake_ai' if lab==0 else 'real'
        row['image'].convert('RGB').save(out/f'{label}_{counts[lab]:03d}.png')
        counts[lab]+=1
        if all(v>=a.n_per_class for v in counts.values()): break
    print('saved',counts,'to',out)
if __name__=='__main__': main()
