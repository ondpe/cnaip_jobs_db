from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import not_
from pydantic import BaseModel
import os
import logging
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

from app.database import init_db, get_db, SessionLocal
from app.models import Source, Job, Setting
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai, last_logs, add_debug_log

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

class SourceCreate(BaseModel):
    name: str
    url: str

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

def cleanup_orphaned_jobs():
    """Smaže pozice, které nepatří k žádnému existujícímu zdroji."""
    db = SessionLocal()
    try:
        # Najdeme ID všech existujících zdrojů
        source_ids = [s.id for s in db.query(Source.id).all()]
        # Smažeme pozice, jejichž source_id není v seznamu existujících zdrojů
        orphaned = db.query(Job).filter(not_(Job.source_id.in_(source_ids))).all()
        if orphaned:
            count = len(orphaned)
            for job in orphaned:
                db.delete(job)
            db.commit()
            logger.info(f"Vyčištěno {count} osiřelých pracovních pozic.")
    except Exception as e:
        logger.error(f"Chyba při čištění osiřelých pozic: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    cleanup_orphaned_jobs()

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()

@app.get("/api/sources")
def get_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()

@app.post("/api/admin/sources", dependencies=[Depends(authenticate_admin)])
def create_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    new_source = Source(name=source_data.name, url=source_data.url)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@app.delete("/api/admin/sources/{source_id}", dependencies=[Depends(authenticate_admin)])
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404, detail="Zdroj nenalezen")
    
    # Nejdříve smažeme všechny pozice navázané na tento zdroj
    db.query(Job).filter(Job.source_id == source_id).delete()
    
    db.delete(source)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/admin/debug/logs", dependencies=[Depends(authenticate_admin)])
def get_debug_logs():
    return {"logs": last_logs}

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
    key_val = setting.value if setting else os.getenv("GEMINI_API_KEY")
    
    if not key_val:
        return {"has_key": False, "masked_key": ""}
    
    masked = key_val[:4] + "...." + key_val[-4:] if len(key_val) > 8 else "****"
    return {"has_key": True, "masked_key": masked}

@app.post("/api/admin/settings/gemini-key", dependencies=[Depends(authenticate_admin)])
def set_gemini_key(key: str, db: Session = Depends(get_db)):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        model.generate_content("ping", generation_config={"max_output_tokens": 1})
    except Exception as e:
        logger.error(f"Neplatný AI klíč: {e}")
        raise HTTPException(status_code=400, detail=f"AI klíč se nepodařilo ověřit: {str(e)}")

    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    if setting:
        setting.value = key
    else:
        db.add(Setting(key="gemini_api_key", value=key))
    db.commit()
    return {"status": "ok"}

def get_active_api_key(db: Session):
    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    if setting and setting.value and len(setting.value) > 5:
        return setting.value
    return os.getenv("GEMINI_API_KEY")

@app.post("/api/admin/run-ai-analysis", dependencies=[Depends(authenticate_admin)])
def run_analysis(db: Session = Depends(get_db)):
    api_key = get_active_api_key(db)
    add_debug_log(f"Spouštím hromadnou analýzu s Gemini 2.0. Klíč nalezen: {bool(api_key)}")
    
    unprocessed = db.query(Job).filter(
        (Job.summary == "") | 
        (Job.summary == None) | 
        (Job.summary.like("%Čeká na AI%")) |
        (Job.summary.like("%Chyba AI%"))
    ).all()
    
    add_debug_log(f"Nalezeno {len(unprocessed)} pozic ke zpracování.")
    
    deleted_count = 0
    analyzed_count = 0
    
    for job in unprocessed:
        analysis = analyze_job_with_ai(job.raw_content or job.title, api_key)
        
        if not analysis.get("is_job", True):
            db.delete(job)
            deleted_count += 1
        else:
            job.keywords = analysis.get("keywords", "")
            job.summary = f"{analysis.get('summary', 'Bez shrnutí')} (Seniorita: {analysis.get('seniority', 'Nezjištěno')})"
            job.last_analyzed_at = datetime.utcnow()
            analyzed_count += 1
    
    db.commit()
    add_debug_log(f"Hromadná analýza dokončena. Zpracováno: {analyzed_count}, Smazáno: {deleted_count}")
    return {"count": analyzed_count, "deleted": deleted_count}

@app.post("/api/admin/analyze-job/{job_id}", dependencies=[Depends(authenticate_admin)])
def analyze_single_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: raise HTTPException(404, detail="Pozice nenalezena")
    
    api_key = get_active_api_key(db)
    add_debug_log(f"Spouštím analýzu jedné pozice ID {job_id}")
    analysis = analyze_job_with_ai(job.raw_content or job.title, api_key)
    
    if not analysis.get("is_job", True):
        db.delete(job)
        db.commit()
        return {"status": "deleted", "reason": "Not a job posting"}
        
    job.keywords = analysis.get("keywords", "")
    job.summary = f"{analysis.get('summary', 'Bez shrnutí')} (Seniorita: {analysis.get('seniority', 'Nezjištěno')})"
    job.last_analyzed_at = datetime.utcnow()
    db.commit()
    return analysis

@app.post("/api/admin/scrape/{source_id}", dependencies=[Depends(authenticate_admin)])
async def run_scrape(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404, detail="Zdroj nenalezen")
    
    add_debug_log(f"Scrapuji zdroj: {source.name}")
    scraped = await scrape_source(source.url, source.name)
    new_count = 0
    for item in scraped:
        title = item['title']
        link = item.get('url')
        existing = db.query(Job).filter(Job.title == title, Job.source_id == source.id).first()
        
        if not existing:
            db.add(Job(
                title=title, company=source.name, 
                location=item.get('location'), raw_content=item.get('raw_content'), 
                link=link, source_id=source.id
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
    add_debug_log(f"Scraping hotov. Nalezeno {len(scraped)}, uloženo {new_count} nových.")
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