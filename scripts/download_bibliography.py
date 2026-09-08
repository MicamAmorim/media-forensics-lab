"""Download legally accessible bibliography declared in bibliography/references.yaml.
Run on a machine with Internet access. It never attempts to bypass paywalls or access controls.
For publisher-only books, it writes a bibliographic note instead of downloading copyrighted text.
"""
from pathlib import Path
import urllib.request, yaml
ROOT=Path(__file__).resolve().parents[1]
refs=yaml.safe_load((ROOT/'bibliography/references.yaml').read_text(encoding='utf-8'))['references']

def main():
    for key,r in refs.items():
        dest=ROOT/'bibliography'/r['file']
        dest.parent.mkdir(parents=True,exist_ok=True)
        if r['type']=='book':
            dest.write_text(f"{r['citation']}\n\nPublisher/official page: {r['url']}\n\nFull text is not bundled unless the rights holder offers a lawful downloadable copy.\n",encoding='utf-8')
            print('NOTE',key,dest)
            continue
        if dest.suffix.lower() not in {'.pdf','.doc','.docx','.txt'} or dest.suffix.lower()=='.txt':
            dest.write_text(f"{r['citation']}\n\nOfficial/project URL: {r['url']}\n",encoding='utf-8')
            print('NOTE',key,dest); continue
        try:
            req=urllib.request.Request(r['url'],headers={'User-Agent':'Mozilla/5.0 MediaForensicsLab/0.1'})
            with urllib.request.urlopen(req,timeout=60) as src, open(dest,'wb') as dst:
                dst.write(src.read())
            print('OK',key,dest)
        except Exception as e:
            fail=dest.with_suffix(dest.suffix+'.download_failed.txt')
            fail.write_text(f"Could not download automatically: {e}\nURL: {r['url']}\nCitation: {r['citation']}\n",encoding='utf-8')
            print('FAIL',key,e)
if __name__=='__main__': main()
