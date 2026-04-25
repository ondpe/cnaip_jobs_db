from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
from datetime import datetime

# Importy
from app.database import init_db, get_db
from app.models import Source, Job, Setting
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Scraper Pro")

try:
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

@app.on_event("startup")
def startup_event():
    if not os.path.exists("data"):
        os.makedirs("data")
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        sources = db.query(Source).all()
        gemini_key = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
        is_supabase = "postgresql" in str(db.get_bind().url)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "jobs": jobs,
            "sources": sources,
            "count": len(jobs),
            "is_supabase": is_supabase,
            "has_gemini_key": bool(gemini_key and gemini_key.value)
        })
    except Exception as e:
        return HTMLResponse(f"<h1>Chyba</h1><p>{str(e)}</p>")

@app.post("/api/settings/gemini-key")
def update_gemini_key(key: str, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    if setting:
        setting.value = key
    else:
        db.add(Setting(key="gemini_api_key", value=key))
    db.commit()
    return {"message": "API klíč byl uložen."}

@app.post("/sources")
def add_source(url: str, name: str, db: Session = Depends(get_db)):
    new_source = Source(url=url, name=name)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@app.post("/scrape/{source_id}")
async def run_scrape(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(404)
    scraped = await scrape_source(source.url, source.name)
    count = 0
    for item in scraped:
        if not db.query(Job).filter(Job.title == item['title'], Job.source_id == source.id).first():
            db.add(Job(title=item['title'], company=item.get('company'), location=item.get('location'), raw_content=item.get('raw_content'), source_id=source.id))
            count += 1
    db.commit()
    return {"jobs_saved": count, "jobs_found": len(scraped)}

@app.post("/jobs/run-ai-analysis")
def run_analysis(db: Session = Depends(get_db)):
    # Získání klíče z DB
    key_setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
    api_key = key_setting.value if key_setting else os.getenv("GEMINI_API_KEY")
    
    unprocessed = db.query(Job).filter((Job.summary == "") | (Job.summary == None)).all()
    for job in unprocessed:
        analysis = analyze_job_with_ai(job.raw_content, api_key)
        job.keywords = analysis["keywords"]
        job.summary = f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
    db.commit()
    return {"message": f"Analyzováno {len(unprocessed)} pozic."}