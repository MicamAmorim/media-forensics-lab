from pathlib import Path
import argparse, shutil, yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('case_id'); ap.add_argument('--from-demo',action='store_true'); a=ap.parse_args()
    c=ROOT/a.case_id; (c/'original').mkdir(parents=True,exist_ok=True); (c/'working').mkdir(exist_ok=True); (c/'results').mkdir(exist_ok=True); (c/'logs').mkdir(exist_ok=True); (c/'final').mkdir(exist_ok=True)
    d=yaml.safe_load((ROOT/'templates'/'case.yaml').read_text(encoding='utf-8')); d['case']['id']=a.case_id; (c/'case.yaml').write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
    if a.from_demo:
        for p in (ROOT/'dataset'/'demo'/'images').glob('*'): shutil.copy2(p,c/'original'/p.name)
        for p in (ROOT/'dataset'/'demo'/'videos').glob('*'): shutil.copy2(p,c/'original'/p.name)
    print(c)
if __name__=='__main__': main()
