from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import init_db, get_db
from app.models import Source, Job
from app import models
from app.scraper import scrape_source
from datetime import datetime
from app.analyzator import analyze_job_with_ai

import os
import logging
import pandas as pd
import io

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cesta k šablonám
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
TEMPLATES_DIR = os.path.join(parent_dir, "templates")

app = FastAPI(title="Job Scraper API")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def startup_event():
    data_dir = os.path.join(parent_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"DB Dir: {data_dir}")
    init_db()

# Testovací endpoint pro ověření funkčnosti
@app.get("/ping", response_class=PlainTextResponse)
def ping():
    return "pong - server is alive"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    logger.info("Request on /")
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        sources = db.query(Source).all()
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "jobs": jobs, 
            "sources": sources,
            "count": len(jobs)
        })
    except Exception as e:
        logger.error(f"Render error: {e}")
        return HTMLResponse(content=f"<h1>Chyba serveru</h1><p>{str(e)}</p>", status_code=500)

# --- ZDROJE ---
@app.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    return {"sources": sources, "count": len(sources)}

@app.post("/sources")
def create_source(url: str, name: str, db: Session = Depends(get_db)):
    new_source = Source(url=url, name=name)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

# --- SCRAPING & AI ---
@app.post("/scrape/{source_id}")
async def scrape_jobs(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404)
    jobs_data = await scrape_source(source.url, source.name)
    saved = 0
    for jd in jobs_data:
        if not db.query(Job).filter(Job.title == jd['title'], Job.source_id == source_id).first():
            db.add(Job(title=jd['title'], company=jd['company'], location=jd['location'], raw_content=jd['raw_content'], source_id=source_id))
            saved += 1
    db.commit()
    return {"jobs_saved": saved}

@app.post("/jobs/run-ai-analysis")
def run_ai_analysis(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.summary == "").all()
    for job in jobs:
        ai = analyze_job_with_ai(job.raw_content)
        job.keywords, job.summary = ai["keywords"], f"{ai['summary']} (Seniorita: {ai['seniority']})"
    db.commit()
    return {"message": f"Zpracováno {len(jobs)} inzerátů."}