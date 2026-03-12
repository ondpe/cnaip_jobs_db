from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse
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

# 1. Nejdříve vytvoříme aplikaci
app = FastAPI(
    title="Job Scraper API",
    description="API for scraping and managing job postings",
    version="1.0.0"
)

# 2. Pak inicializujeme šablony
templates = Jinja2Templates(directory="templates")

# 3. HOME PAGE - Tady vracíme ten pěkný web
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "jobs": jobs, 
        "count": len(jobs)
    })

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    os.makedirs("./data", exist_ok=True)
    init_db()

# --- ZDROJE (SOURCES) ---
@app.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    return {"sources": sources, "count": len(sources)}

@app.post("/sources")
def create_source(url: str, name: str, is_active: bool = True, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == url).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Source with URL '{url}' already exists")
    
    new_source = Source(url=url, name=name, is_active=is_active)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return {"message": "Source created successfully", "source": new_source}

@app.post("/sources/import-excel")
async def import_from_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        if 'url' not in df.columns or 'name' not in df.columns:
            raise HTTPException(status_code=400, detail="Excel musí obsahovat sloupce 'url' a 'name'")

        new_sources_count = 0
        for _, row in df.iterrows():
            url_val = str(row['url']).strip()
            name_val = str(row['name']).strip()

            existing = db.query(Source).filter(Source.url == url_val).first()
            if not existing:
                new_source = Source(url=url_val, name=name_val, is_active=True)
                db.add(new_source)
                new_sources_count += 1
        
        db.commit()
        return {"message": f"Úspěšně importováno {new_sources_count} nových zdrojů z Excelu."}
    except Exception as e:
        logger.error(f"Excel import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Nepodařilo se zpracovat Excel: {str(e)}")

# --- PRÁCE (JOBS) ---
@app.get("/jobs")
def get_jobs(limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(Job).limit(limit).all()
    return {"jobs": jobs, "count": len(jobs)}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/scrape/{source_id}")
async def scrape_jobs(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source with ID {source_id} not found")
    
    try:
        jobs_data = await scrape_source(source.url, source.name)
        saved_count = 0
        
        for job_data in jobs_data:
            existing_job = db.query(Job).filter(
                Job.title == job_data['title'],
                Job.source_id == source_id
            ).first()
            
            if existing_job:
                continue
            
            new_job = Job(
                title=job_data.get('title', 'Untitled'),
                company=job_data.get('company', ''),
                location=job_data.get('location', ''),
                keywords='', # Upraveno, aby se neplnilo URL adresou
                summary='',
                raw_content=job_data.get('raw_content', ''),
                source_id=source_id,
                created_at=datetime.utcnow()
            )
            db.add(new_job)
            saved_count += 1
        
        db.commit()
        return {
            "source_name": source.name,
            "jobs_found": len(jobs_data),
            "jobs_saved": saved_count,
            "message": f"Successfully scraped {saved_count} new jobs"
        }
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/jobs/run-ai-analysis")
def run_ai_analysis(db: Session = Depends(get_db)):
    jobs_to_analyse = db.query(Job).filter(Job.summary == "").all()
    analysed_count = 0
    for job in jobs_to_analyse:
        ai_results = analyze_job_with_ai(job.raw_content)
        job.keywords = ai_results["keywords"]
        job.summary = ai_results["summary"]
        job.summary += f" (Seniorita: {ai_results['seniority']})"
        analysed_count += 1
    db.commit()
    return {"message": f"Analýza dokončena. Zpracováno {analysed_count} inzerátů."}