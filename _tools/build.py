"""Build the public site from the claude.ai artifact HTML.
Usage: python3 _tools/build.py <artifact.html> <assets_dir> [repo_dir]
- artifact.html: the page HTML saved from the claude.ai artifact (full doc or fragment)
- assets_dir: folder holding downloaded photo assets named <32-hex-id>.<ext>
Prints any photo ids that are referenced but missing (download those, then rerun)."""
import re,os,sys,json,glob
from PIL import Image
SRC,RAW=sys.argv[1],sys.argv[2]; OUT=sys.argv[3] if len(sys.argv)>3 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT+'/img',exist_ok=True)
s=open(SRC,encoding='utf-8').read()
if '<body>' in s[:3000]:
    s=s[s.index('<body>')+6:]
    if s.rstrip().endswith('</body></html>'): s=s.rstrip()[:-len('</body></html>')]
D=json.loads(re.search(r'id="site-data">(.*?)</script>',s,re.S).group(1))
ids=set(v for v in D.get('photos',{}).values() if v)|set(re.findall(r'/_blob/([0-9a-f]{32})',s))
ext={}
for f in glob.glob(OUT+'/img/*'):
    b,e=os.path.splitext(os.path.basename(f))
    if re.fullmatch(r'[0-9a-f]{32}',b): ext[b]=e
missing=[]
for i in sorted(ids):
    if i in ext: continue
    src=[f for f in glob.glob(f'{RAW}/{i}.*')]
    if not src: missing.append(i); continue
    f=src[0]; e=os.path.splitext(f)[1].lower()
    if e in ('.mp4','.webm','.mov'):
        import shutil; shutil.copy(f,f'{OUT}/img/{i}{e}'); ext[i]=e; continue
    im=Image.open(f); alpha=False
    if im.mode in('RGBA','LA','P'):
        a=im.convert('RGBA').split()[3]; alpha=a.getextrema()[0]<250
    im.thumbnail((2200,2200))
    if alpha or e=='.webp': im.save(f'{OUT}/img/{i}.webp','WEBP',quality=85); ext[i]='.webp'
    else: im.convert('RGB').save(f'{OUT}/img/{i}.jpg','JPEG',quality=84,optimize=True,progressive=True); ext[i]='.jpg'
if missing:
    print('MISSING_ASSETS '+' '.join(missing)); sys.exit(2)
used={i:ext[i] for i in ids}
mapjs='var BLOB_EXT='+json.dumps(used)+';function blobUrl(i){return "img/"+i+(BLOB_EXT[i]||".jpg");}\n'
s=s.replace('\'<video src="/_blob/\' + esc(id) + \'"','\'<video src="\' + blobUrl(id) + \'"')
s=s.replace('\'<img src="/_blob/\' + esc(id) + \'"','\'<img src="\' + blobUrl(id) + \'"')
s=re.sub(r'/_blob/([0-9a-f]{32})',lambda m:'img/'+m.group(1)+used.get(m.group(1),'.jpg'),s)
k=s.index('<script id="app-js">')+len('<script id="app-js">'); s=s[:k]+'\n'+mapjs+s[k:]
head='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex,nofollow"><meta name="description" content="Ashley &amp; Eric · October 2, 2027 · Deià, Mallorca"><link rel="icon" href="img/favicon.png"><style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n'
open(OUT+'/index.html','w',encoding='utf-8').write(head+s+'\n</body></html>\n')
for n,c in (('CNAME','ashanderic.com\n'),('.nojekyll',''),('robots.txt','User-agent: *\nDisallow: /\n')):
    if not os.path.exists(f'{OUT}/{n}'): open(f'{OUT}/{n}','w').write(c)
print('BUILD_OK', len(used),'photos')
