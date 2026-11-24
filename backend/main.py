from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.store import init, search, sources
from backend.agent import recommend
import os

@asynccontextmanager
async def lifespan(app):
    init()
    yield

app=FastAPI(title='OpportunityIQ',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('FRONTEND_ORIGIN','http://localhost:3000')],allow_methods=['GET','POST'],allow_headers=['Content-Type'])

class MatchRequest(BaseModel):
    profile: str=Field(max_length=20000)
    q: str=Field(default='',max_length=200)
    location: str=Field(default='',max_length=100)
    remote: bool=False
    page: int=Field(default=1,ge=1)
    limit: int=Field(default=20,ge=1,le=100)

@app.get('/health')
def health(): return {'status':'ok'}

@app.get('/jobs')
def jobs(q:str=Query('',max_length=200),location:str=Query('',max_length=100),remote:bool=False,page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100)):
    return search(q,location,remote,page=page,limit=limit)

@app.post('/match')
def match(req:MatchRequest): return search(**req.model_dump())

@app.get('/sources')
def source_status(): return {'sources':sources()}

class RecommendRequest(BaseModel):
    profile: str=Field(min_length=1,max_length=20000)
    q: str=Field(default='',max_length=200)
    location: str=Field(default='',max_length=100)
    remote: bool=False
    consent: bool=False

@app.post('/recommend')
def recommendations(req:RecommendRequest):
    if not req.consent: raise HTTPException(400,'Explicit consent to send profile text to OpenAI is required')
    if not os.getenv('OPENAI_API_KEY'): raise HTTPException(503,'AI recommendations are not configured; use standard skill matching instead')
    try: return recommend(**req.model_dump(exclude={'consent'}))
    except Exception: raise HTTPException(502,'Live AI request failed; no recommendations generated')
