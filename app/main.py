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
from app.scraper import scrape_source, fetch_job_detail
from app.analyzator import analyze_job_with_ai, is_likely_job, last_logs, add_debug_log

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

class SourceCreate(BaseModel):
    name: str
    url: str

class BulkAction(BaseModel):
    ids: List[int]

class CredentialsUpdate(BaseModel):
    username: str
    password: str

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    db_user = db.query(Setting).filter(Setting.key == "admin_username").first()
    db_pass = db.query(Setting).filter(Setting.key == "admin_password").first()
    
    admin_user = db_user.value if db_user else os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = db_pass.value if db_pass else os.getenv("ADMIN_PASSWORD", "admin123")
    
    if credentials.username != admin_user or credentials.password != admin_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatné přihlašovací údaje"
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

@app.post("/api/admin/jobs/bulk-delete", dependencies=[Depends(authenticate_admin)])
def bulk_delete_jobs(action: BulkAction, db: Session = Depends(get_db)):
    db.query(Job).filter(Job.id.in_(action.ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "deleted", "count": len(action.ids)}

@app.get("/api/admin/settings/gemini-key", dependencies=[Depends(authenticate_admin)])
def get_gemini_key(db: Session = Depends(get_db)):
    key_setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    model_setting = db.query(Setting).filter(Setting.key == "gemini_model_name").first()
    key_val = key_setting.value if key_setting else os.getenv("GEMINI_API_KEY")
    model_val = model_setting.value if model_setting else "gemini-1.5-flash"
    if not key_val: return {"has_key": False, "masked_key": "", "model_name": model_val}
    masked = key_val[:4] + "...." + key_val[-4:] if len(key_val) > 8 else "****"
    return {"has_key": True, "masked_key": masked, "model_name": model_val}

@app.get("/api/admin/settings/list-models", dependencies=[Depends(authenticate_admin)])
def list_available_models(key: str):
    try:
        clean_key = key.strip()
        genai.configure(api_key=clean_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append({"name": m.name.replace('models/', ''), "display_name": m.display_name})
        return models
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/settings/gemini-key", dependencies=[Depends(authenticate_admin)])
def set_gemini_key(key: str, model_name: Optional[str] = "gemini-1.5-flash", db: Session = Depends(get_db)):
    try:
        clean_key = key.strip()
        genai.configure(api_key=clean_key)
        model = genai.GenerativeModel(model_name)
        model.generate_content("ping", generation_config={"max_output_tokens": 1})
        for k, v in {"gemini_api_key": clean_key, "gemini_model_name": model_name}.items():
            setting = db.query(Setting).filter(Setting.key == k).first()
            if setting: setting.value = v
            else: db.add(Setting(key=k, value=v))
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ověření selhalo: {str(e)}")

@app.post("/api/admin/settings/credentials", dependencies=[Depends(authenticate_admin)])
def update_credentials(creds: CredentialsUpdate, db: Session = Depends(get_db)):
    for k, v in {"admin_username": creds.username, "admin_password": creds.password}.items():
        setting = db.query(Setting).filter(Setting.key == k).first()
        if setting: setting.value = v
        else: db.add(Setting(key=k, value=v))
    db.commit()
    return {"status": "ok"}

def get_ai_config(db: Session):
    key_setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    model_setting = db.query(Setting).filter(Setting.key == "gemini_model_name").first()
    api_key = (key_setting.value if key_setting and key_setting.value else os.getenv("GEMINI_API_KEY", "")).strip()
    model_name = model_setting.value if model_setting and model_setting.value else "gemini-1.5-flash"
    return api_key, model_name

@app.post("/api/admin/run-ai-analysis", dependencies=[Depends(authenticate_admin)])
async def run_analysis(db: Session = Depends(get_db)):
    api_key, model_name = get_ai_config(db)
    unprocessed = db.query(Job).filter(
        (Job.summary == "") | (Job.summary == None) | (Job.summary.like("%Čeká na AI%")) | (Job.summary.like("%Chyba AI%"))
    ).all()
    
    total = len(unprocessed)
    add_debug_log(f"Spouštím hromadnou analýzu pro {total} pozic...")
    
    analyzed_count = 0
    deleted_count = 0
    for i, job in enumerate(unprocessed):
        add_debug_log(f"[{i+1}/{total}] Zpracovávám: {job.title} ({job.company})")
        if (not job.raw_content or len(job.raw_content) < 500) and job.link:
            add_debug_log(f"   Stahuji detail z {job.link}")
            full_text = await fetch_job_detail(job.link)
            if full_text:
                job.raw_content = full_text
                db.commit()

        analysis = analyze_job_with_ai(job.raw_content or job.title, api_key, model_name)
        if not analysis.get("is_job", True):
            add_debug_log(f"   AI: Není to job, mažu.")
            db.delete(job)
            deleted_count += 1
        else:
            seniority = analysis.get("seniority", "Medior")
            tech_keywords = analysis.get("keywords", "")
            job.keywords = f"{seniority}, {tech_keywords}" if tech_keywords else seniority
            job.summary = analysis.get('summary', 'Bez shrnutí')
            job.last_analyzed_at = datetime.utcnow()
            analyzed_count += 1
            add_debug_log(f"   AI: Ok ({seniority})")
        db.commit()
    
    add_debug_log(f"Analýza dokončena. Zpracováno: {analyzed_count}, Smazáno: {deleted_count}")
    return {"count": analyzed_count, "deleted": deleted_count}

@app.post("/api/admin/jobs/bulk-analyze", dependencies=[Depends(authenticate_admin)])
async def bulk_analyze_jobs(action: BulkAction, db: Session = Depends(get_db)):
    api_key, model_name = get_ai_config(db)
    jobs_to_analyze = db.query(Job).filter(Job.id.in_(action.ids)).all()
    
    total = len(jobs_to_analyze)
    add_debug_log(f"Spouštím vybranou analýzu pro {total} pozic...")
    
    count = 0
    deleted = 0
    for i, job in enumerate(jobs_to_analyze):
        add_debug_log(f"[{i+1}/{total}] Zpracovávám: {job.title} ({job.company})")
        if (not job.raw_content or len(job.raw_content) < 500) and job.link:
            full_text = await fetch_job_detail(job.link)
            if full_text:
                job.raw_content = full_text
                db.commit()

        analysis = analyze_job_with_ai(job.raw_content or job.title, api_key, model_name)
        if not analysis.get("is_job", True):
            db.delete(job)
            deleted += 1
        else:
            seniority = analysis.get("seniority", "Medior")
            tech_keywords = analysis.get("keywords", "")
            job.keywords = f"{seniority}, {tech_keywords}" if tech_keywords else seniority
            job.summary = analysis.get('summary', 'Bez shrnutí')
            job.last_analyzed_at = datetime.utcnow()
            count += 1
        db.commit()
    
    add_debug_log(f"Hromadná analýza hotova. Ok: {count}, Smazáno: {deleted}")
    return {"count": count, "deleted": deleted}

@app.post("/api/admin/analyze-job/{job_id}", dependencies=[Depends(authenticate_admin)])
async def analyze_single_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: raise HTTPException(404, detail="Pozice nenalezena")
    
    add_debug_log(f"Manuální analýza: {job.title}")
    if (not job.raw_content or len(job.raw_content) < 500) and job.link:
        full_text = await fetch_job_detail(job.link)
        if full_text:
            job.raw_content = full_text
            db.commit()

    api_key, model_name = get_ai_config(db)
    analysis = analyze_job_with_ai(job.raw_content or job.title, api_key, model_name)
    
    if not analysis.get("is_job", True):
        add_debug_log("   AI: Není to job, mažu.")
        db.delete(job)
        db.commit()
        return {"status": "deleted"}
    
    seniority = analysis.get("seniority", "Medior")
    tech_keywords = analysis.get("keywords", "")
    job.keywords = f"{seniority}, {tech_keywords}" if tech_keywords else seniority
    job.summary = analysis.get('summary', 'Bez shrnutí')
    job.last_analyzed_at = datetime.utcnow()
    db.commit()
    add_debug_log(f"   AI: Hotovo ({seniority})")
    return analysis

@app.post("/api/admin/scrape/{source_id}", dependencies=[Depends(authenticate_admin)])
async def run_scrape(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404, detail="Zdroj nenalezen")
    
    add_debug_log(f"Spouštím scraping zdroje: {source.name} ({source.url})")
    api_key, model_name = get_ai_config(db)
    scraped = await scrape_source(source.url, source.name)
    
    add_debug_log(f"Nalezeno {len(scraped)} odkazů. Provádím rychlou filtraci...")
    
    new_count = 0
    skipped_count = 0
    for i, item in enumerate(scraped):
        existing = db.query(Job).filter(Job.title == item['title'], Job.source_id == source.id).first()
        if not existing:
            # Rychlá AI filtrace před uložením
            if is_likely_job(item['title'], item.get('url', ''), api_key, model_name):
                db.add(Job(title=item['title'], company=source.name, location=item.get('location'), raw_content=item.get('raw_content'), link=item.get('url'), source_id=source.id))
                new_count += 1
            else:
                skipped_count += 1
        else:
            add_debug_log(f"   Duplicita: {item['title']}")
                
    source.last_crawled_at = datetime.utcnow()
    source.last_scrape_count = new_count
    source.last_scrape_found = len(scraped)
    db.commit()
    add_debug_log(f"Scraping hotov. Nových: {new_count}, Vyfiltrováno jako ne-job: {skipped_count}")
    return {"new": new_count, "skipped": skipped_count, "total": len(scraped)}

frontend_dist = os.path.join(os.getcwd(), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api"): raise HTTPException(404)
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.isfile(file_path): return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_dist, "index.html"))