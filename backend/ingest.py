import argparse, json, sys, time
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from backend.store import normalize, refresh_board, source_failure

class PlainText(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,data): self.parts.append(data)
    def handle_starttag(self,tag,attrs):
        if tag in ('p','div','br','li','h1','h2','h3'): self.parts.append(' ')

def strip_html(value):
    from html import unescape
    p=PlainText(); p.feed(unescape(value or '')); return ' '.join(''.join(p.parts).split())

def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'OpportunityIQ/0.1 (portfolio job discovery)','Accept':'application/json'}),timeout=25) as r:
                raw=r.read(30_000_001)
                if len(raw)>30_000_000: raise ValueError('Response exceeds size limit; no snapshot published')
                return json.loads(raw)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2: raise
        except (URLError,TimeoutError):
            if attempt==2: raise
        time.sleep(2**attempt)

def greenhouse(board,company):
    data=fetch(f'https://boards-api.greenhouse.io/v1/boards/{quote(board,safe="")}/jobs?content=true')
    if not isinstance(data.get('jobs'),list): raise ValueError('Unexpected Greenhouse payload')
    if data.get('meta',{}).get('total',len(data['jobs']))!=len(data['jobs']): raise ValueError('Incomplete board response')
    return [normalize(j['title'],company,j.get('location',{}).get('name',''),strip_html(j.get('content')),j['absolute_url'],'greenhouse',j['id'],j.get('updated_at'),board=board) for j in data['jobs']]

def lever(board,company):
    rows=[]; skip=0; size=100
    while True:
        data=fetch(f'https://api.lever.co/v0/postings/{quote(board,safe="")}?mode=json&limit={size}&skip={skip}')
        if not isinstance(data,list): raise ValueError('Unexpected Lever payload')
        if data and any(j['id'] in {r['source_id'] for r in rows} for j in data): raise ValueError('Repeated page; no snapshot published')
        for j in data:
            cats=j.get('categories') or {}; loc=', '.join(cats.get('allLocations') or []) or cats.get('location','')
            body=' '.join([j.get('descriptionPlain') or strip_html(j.get('description')), *[strip_html(x.get('content')) for x in j.get('lists',[])],j.get('additionalPlain') or strip_html(j.get('additional'))])
            rows.append(normalize(j['text'],company,loc,body,j['hostedUrl'],'lever',j['id'],board=board,workplace=j.get('workplaceType') or '',employment=cats.get('commitment',''),salary=j.get('salaryRange')))
        if len(data)<size: break
        skip+=size
        if skip>10000: raise ValueError('Board pagination safety limit reached')
    return rows

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',default='boards.json'); args=p.parse_args()
    failed=0; total=0
    with open(args.config) as f: boards=json.load(f)
    if not boards: print('No employer boards configured',file=sys.stderr); return 1
    for b in boards:
        try:
            jobs={'greenhouse':greenhouse,'lever':lever}[b['source']](b['board'],b['company']); count=refresh_board(b['source'],b['board'],b['company'],jobs); total+=count; print(f"{b['company']}: {count} real source records")
        except Exception as e:
            failed+=1; source_failure(b['source'],b['board'],b['company'],e); print(f"{b['company']}: {e}",file=sys.stderr)
    print(json.dumps({'successful_boards':len(boards)-failed,'failed_boards':failed,'observed_jobs':total}))
    return int(failed>0)
if __name__=='__main__': raise SystemExit(main())
