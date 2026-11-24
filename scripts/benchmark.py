"""Measure real indexed records and local search latency after successful ingestion."""
import json, time, statistics
from backend.store import all_jobs, search, sources

def main():
    jobs=all_jobs(); statuses=sources()
    if not jobs or not statuses or any(s['status']!='ok' for s in statuses):
        raise SystemExit('No complete successful live snapshot; benchmark not published')
    queries=['software engineer','python','data engineer','react','machine learning']
    results=[]
    for q in queries:
        durations=[]
        for _ in range(10):
            start=time.perf_counter(); result=search(q=q); durations.append((time.perf_counter()-start)*1000)
        results.append({'query':q,'results':result['total'],'median_ms':round(statistics.median(durations),3),'runs':len(durations)})
    print(json.dumps({'indexed_jobs':len(jobs),'sources':statuses,'search_measurements':results},indent=2))
if __name__=='__main__': main()
