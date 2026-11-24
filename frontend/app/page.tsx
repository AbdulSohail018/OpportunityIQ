'use client';
import {useState,useEffect} from 'react';
type Job={id:string;title:string;company:string;location:string;description:string;url:string;source:string;remote:boolean;last_seen:string;match_score?:number|null;matched_skills?:string[];missing_skills?:string[]};
type Source={company:string;status:string;last_success:string|null;count:number};
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
async function request(path:string,body?:unknown){
 const r=await fetch(API+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!r.ok)throw new Error('Request failed ('+r.status+')');
 return r.json();
}
export default function Home(){
 const [q,Q]=useState(''),[location,L]=useState(''),[remote,R]=useState(false),[profile,P]=useState(''),[consent,C]=useState(false);
 const [jobs,J]=useState<Job[]>([]),[total,T]=useState(0),[page,S]=useState(1),[loading,B]=useState(false),[error,E]=useState('');
 const [saved,V]=useState<string[]>([]),[onlySaved,O]=useState(false),[sources,U]=useState<Source[]>([]);
 const [recommendations,A]=useState<{job:Job;reason:string}[]>([]);
 const [model,M]=useState('');
 async function load(n=1){
 B(true);E('');A([]);M('');
 try{const params={q,location,remote,page:n,limit:20};const data=profile.trim()?await request('/match',{...params,profile}):await request('/jobs?'+new URLSearchParams({q,location,remote:String(remote),page:String(n),limit:'20'}));
 J(data.jobs);T(data.total);S(n);U((await request('/sources')).sources);
 }catch(e){E(e instanceof Error?e.message:'Unable to load jobs');J([]);T(0);}finally{B(false);}
 }
 useEffect(()=>{try{V(JSON.parse(localStorage.getItem('opportunityiq-saved')||'[]'));}catch{}void load();},[]);
 function toggle(id:string){const next=saved.includes(id)?saved.filter(x=>x!==id):[...saved,id];V(next);localStorage.setItem('opportunityiq-saved',JSON.stringify(next));}
 async function ai(){B(true);E('');A([]);M('');try{const data=await request('/recommend',{profile,q,location,remote,consent});A(data.recommendations);M(data.model);}catch(e){E(e instanceof Error?e.message:'AI request failed');}finally{B(false);}}
 function card(j:Job,reason?:string){return <article key={j.id}><div className="jobtop"><div><small>{j.company}</small><h2>{j.title}</h2><p>{j.location||'Location not specified'} {j.remote?' · Remote':''}</p></div><button className="secondary" onClick={()=>toggle(j.id)}>{saved.includes(j.id)?'Saved ✓':'Save'}</button></div>{j.match_score!=null&&<p className="match">Skill overlap: {j.match_score}% · {(j.matched_skills||[]).join(', ')||'No recognized overlap'}</p>}{reason&&<p>{reason}</p>}<details><summary>Job description</summary><p>{j.description}</p>{!!j.missing_skills?.length&&<p>Other mentioned skills: {j.missing_skills.join(', ')}</p>}</details><footer><small>Source: {j.source} · Retrieved {new Date(j.last_seen).toLocaleDateString()}</small><a href={j.url} target="_blank" rel="noopener noreferrer">Employer listing ↗</a></footer></article>}
 return <main><header><span className="logo">OpportunityIQ</span><h1>Find your next opportunity.</h1><p>Search real employer listings. No invented jobs or sponsored rankings.</p></header><section className="panel"><form onSubmit={e=>{e.preventDefault();void load();}}><div className="fields"><label>Role or skill<input value={q} onChange={e=>Q(e.target.value)} placeholder="Software engineer"/></label><label>Location<input value={location} onChange={e=>L(e.target.value)} placeholder="California"/></label></div><label className="check"><input type="checkbox" checked={remote} onChange={e=>R(e.target.checked)}/>Remote only</label><label>Candidate skills or resume text (optional)<textarea value={profile} onChange={e=>P(e.target.value)} maxLength={20000} placeholder="Python, React, SQL..."/></label><div className="actions"><button disabled={loading} type="submit">Search jobs</button><label className="check"><input type="checkbox" checked={consent} onChange={e=>C(e.target.checked)}/>Allow profile text to be sent to the external AI provider</label><button type="button" className="secondary" disabled={loading||!consent||!profile.trim()} onClick={()=>void ai()}>AI recommendations</button></div><small>Skill overlap measures recognized terms, not hiring probability. Remove personal details before submitting a profile.</small></form></section>{error&&<p role="alert" className="error">{error}</p>}{model&&<section><h2>AI recommendations ({model})</h2>{recommendations.length?recommendations.map(x=>card(x.job,x.reason)):<p>No recommendations returned.</p>}</section>}<div className="results"><h2>{loading?'Loading…':total+' matching jobs'}</h2><label className="check"><input type="checkbox" checked={onlySaved} onChange={e=>O(e.target.checked)}/>Saved on this page</label></div>{!loading&&!jobs.length&&!error&&<p>No current results. Check source status or try a different search.</p>}{jobs.filter(j=>!onlySaved||saved.includes(j.id)).map(j=>card(j))}<nav className="actions"><button disabled={loading||page<=1} onClick={()=>void load(page-1)}>Previous</button><span>Page {page}</span><button disabled={loading||page*20>=total} onClick={()=>void load(page+1)}>Next</button></nav><section className="panel"><h2>Employer source status</h2>{sources.length?sources.map(s=><p key={s.company}>{s.company}: {s.status} · {s.count} records at last successful refresh {s.last_success?new Date(s.last_success).toLocaleString():'(none)'}</p>):<p>No ingestion history available.</p>}</section></main>
}
