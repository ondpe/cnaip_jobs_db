from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import logging
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db, get_db
from app.models import Source, Job, Setting
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CNAIP Jobs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[str] = None
    link: Optional[str] = None

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if credentials.username != admin_user or credentials.password != admin_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatné přihlašovací údaje",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()

@app.get("/api/sources")
def get_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()

@app.delete("/api/admin/jobs/{job_id}", dependencies=[Depends(authenticate_admin)])
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: raise HTTPException(404, detail="Pozice nenalezena")
    db.delete(job)
    db.commit()
    return {"status": "deleted"}

@app.patch("/api/admin/jobs/{job_id}", dependencies=[Depends(authenticate_admin)])
def update_job(job_id: int, job_update: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: raise HTTPException(404, detail="Pozice nenalezena")
    
    update_data = job_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    
    db.commit()
    return job

@app.get("/api/admin/settings/gemini-key", dependencies=[Depends(authenticate_admin)])
def get_gemini_key(db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    env_key = os.getenv("GEMINI_API_KEY")
    return {"has_key": bool((setting and setting.value) or env_key)}

@app.post("/api/admin/settings/gemini-key", dependencies=[Depends(authenticate_admin)])
def set_gemini_key(key: str, db: Session = Depends(get_db)):
    logger.info(f"Pokus o uložení AI klíče (délka: {len(key)})")
    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    if setting:
        setting.value = key
    else:
        db.add(Setting(key="gemini_api_key", value=key))
    db.commit()
    logger.info("AI klíč byl úspěšně uložen do databáze.")
    return {"status": "ok"}

def get_active_api_key(db: Session):
    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    if setting and setting.value:
        return setting.value
    return os.getenv("GEMINI_API_KEY")

@app.post("/api/admin/run-ai-analysis", dependencies=[Depends(authenticate_admin)])
def run_analysis(db: Session = Depends(get_db)):
    api_key = get_active_api_key(db)
    if not api_key:
        logger.warning("AI Analýza spuštěna bez API klíče. Bude použit fallback.")
    
    unprocessed = db.query(Job).filter((Job.summary == "") | (Job.summary == None)).all()
    logger.info(f"Spouštím hromadnou analýzu pro {len(unprocessed)} pozic.")
    
    for job in unprocessed:
        analysis = analyze_job_with_ai(job.raw_content or job.title, api_key)
        job.keywords = analysis["keywords"]
        job.summary = f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
        job.last_analyzed_at = datetime.utcnow()
    
    db.commit()
    return {"count": len(unprocessed)}

@app.post("/api/admin/analyze-job/{job_id}", dependencies=[Depends(authenticate_admin)])
def analyze_single_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: raise HTTPException(404, detail="Pozice nenalezena")
    
    api_key = get_active_api_key(db)
    logger.info(f"Analyzuji pozici {job.id} s klíčem: {'Ano' if api_key else 'Ne'}")
    
    analysis = analyze_job_with_ai(job.raw_content or job.title, api_key)
    job.keywords = analysis["keywords"]
    job.summary = f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
    job.last_analyzed_at = datetime.utcnow()
    
    db.commit()
    return analysis

@app.post("/api/admin/scrape/{source_id}", dependencies=[Depends(authenticate_admin)])
async def run_scrape(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404, detail="Zdroj nenalezen")
    
    scraped = await scrape_source(source.url, source.name)
    new_count = 0
    for item in scraped:
        title = item['title']
        link = item.get('url')
        
        existing = db.query(Job).filter(Job.title == title, Job.source_id == source.id).first()
        
        if not existing:
            db.add(Job(
                title=title, 
                company=source.name, 
                location=item.get('location'), 
                raw_content=item.get('raw_content'), 
                link=link,
                source_id=source.id
            ))
            new_count += 1
        else:
            existing.company = source.name
            if not existing.link and link:
                existing.link = link
    
    source.last_crawled_at = datetime.utcnow()
    source.last_scrape_count = new_count
    source.last_scrape_found = len(scraped)
    db.commit()
    return {"new": new_count, "total": len(scraped)}

frontend_dist = os.path.join(os.getcwd(), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api"): raise HTTPException(404)
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.isfile(file_path): return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_dist, "index.html"))