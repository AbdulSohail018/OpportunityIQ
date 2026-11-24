import os, sqlite3, re, hashlib, json
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

DB = os.getenv('DATABASE_PATH', 'data/jobs.db')
SKILLS = ['python','java','javascript','typescript','react','next.js','sql','postgresql','redis','elasticsearch','kafka','spark','aws','gcp','azure','docker','kubernetes','fastapi','spring boot','langgraph','langchain','llm','machine learning','airflow','dbt','go','rust','c++','node.js','firebase','stripe','snowflake','databricks','mongodb','cassandra','scala','graphql','terraform','linux','git','pytorch','tensorflow','html','css','rest','rest api','power bi','tableau']

def skills(text):
    return sorted(s for s in SKILLS if re.search(r'(?<![\w])'+re.escape(s)+r'(?![\w])', text.lower()))

def now_iso(): return datetime.now(timezone.utc).isoformat()

def normalize(title, company, location, description, url, source, source_id, posted_at=None, board='', workplace='', employment='', salary=None):
    clean = lambda x: ' '.join((x or '').split())
    title, company, location, description = map(clean,(title,company,location,description))
    if not title or not company or urlsplit(url).scheme!='https' or not urlsplit(url).netloc:
        raise ValueError('Missing title/company or invalid apply URL')
    key = hashlib.sha256(f'{source}|{board or company.casefold()}|{source_id}'.encode()).hexdigest()[:24]
    workplace=clean(workplace).lower()
    if not workplace:
        workplace='hybrid' if re.search(r'\bhybrid\b',location,re.I) else ('remote' if re.search(r'\bremote\b',location,re.I) else 'unspecified')
    return dict(id=key,title=title,company=company,location=location,description=description,url=url,source=source,board=board,source_id=str(source_id),source_updated_at=posted_at,skills=skills(title+' '+description),remote=workplace=='remote',workplace=workplace,employment=clean(employment),salary=salary)

@contextmanager
def connect():
    Path(DB).parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB, timeout=15)
    con.row_factory=sqlite3.Row
    try:
        con.execute('PRAGMA journal_mode=WAL')
        yield con
        con.commit()
    except Exception:
        con.rollback(); raise
    finally: con.close()

def init():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated TEXT NOT NULL)')
        c.execute('CREATE VIRTUAL TABLE IF NOT EXISTS job_search USING fts5(id UNINDEXED, title, company, location, description, skills)')
        c.execute('CREATE TABLE IF NOT EXISTS sources (source TEXT, board TEXT, company TEXT, last_success TEXT, last_attempt TEXT, status TEXT, count INTEGER, error TEXT, PRIMARY KEY(source,board))')

def _upsert(c,rows,now):
    for j in rows:
        j={**j,'last_seen':now}
        c.execute('INSERT INTO jobs VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(j['id'],json.dumps(j),now))
        c.execute('DELETE FROM job_search WHERE id=?',(j['id'],))
        c.execute('INSERT INTO job_search VALUES(?,?,?,?,?,?)',(j['id'],j['title'],j['company'],j['location'],j['description'],' '.join(j['skills'])))

def upsert(rows):
    init()
    with connect() as c: _upsert(c,rows,now_iso())

def refresh_board(source,board,company,rows):
    init(); now=now_iso(); unique={j['id']:j for j in rows}
    with connect() as c:
        old=c.execute("SELECT id FROM jobs WHERE json_extract(payload,'$.source')=? AND json_extract(payload,'$.board')=?",(source,board)).fetchall()
        for r in old:
            if r['id'] not in unique:
                c.execute('DELETE FROM job_search WHERE id=?',(r['id'],));c.execute('DELETE FROM jobs WHERE id=?',(r['id'],))
        _upsert(c,unique.values(),now)
        c.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source,board) DO UPDATE SET company=excluded.company,last_success=excluded.last_success,last_attempt=excluded.last_attempt,status=excluded.status,count=excluded.count,error=NULL',(source,board,company,now,now,'ok',len(unique),None))
    return len(unique)

def source_failure(source,board,company,error):
    init()
    with connect() as c:
        c.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source,board) DO UPDATE SET last_attempt=excluded.last_attempt,status=excluded.status,error=excluded.error',(source,board,company,None,now_iso(),'error',0,str(error)[:300]))

def sources():
    init()
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM sources ORDER BY company')]

def all_jobs():
    init()
    with connect() as c: return [json.loads(r[0]) for r in c.execute('SELECT payload FROM jobs ORDER BY id')]

def search(q='',location='',remote=False,profile='',page=1,limit=20):
    init(); tokens=re.findall(r'\w+',q.lower())[:12]
    cutoff=(datetime.now(timezone.utc)-timedelta(days=int(os.getenv('MAX_AGE_DAYS','7')))).isoformat()
    with connect() as c:
        if tokens:
            query=' OR '.join('"'+t+'"' for t in tokens)
            rows=c.execute('SELECT j.payload FROM job_search s JOIN jobs j ON j.id=s.id WHERE job_search MATCH ? AND j.updated>=? ORDER BY bm25(job_search,0,5,2,1,1,3),j.id',(query,cutoff))
        else: rows=c.execute('SELECT payload FROM jobs WHERE updated>=? ORDER BY updated DESC,id',(cutoff,))
        jobs=[json.loads(r[0]) for r in rows]
    wanted=set(skills(profile)); results=[]
    for j in jobs:
        if location.casefold() not in j['location'].casefold() or (remote and not j['remote']): continue
        if profile.strip():
            matched=sorted(wanted & set(j['skills'])); missing=sorted(set(j['skills'])-wanted)
            j={**j,'match_score':round(100*len(matched)/len(j['skills'])) if j['skills'] else None,'matched_skills':matched,'missing_skills':missing}
        results.append(j)
    if profile.strip(): results.sort(key=lambda j:j['match_score'] if j['match_score'] is not None else -1,reverse=True)
    return {'total':len(results),'page':page,'limit':limit,'jobs':results[(page-1)*limit:page*limit]}
