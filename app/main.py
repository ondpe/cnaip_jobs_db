from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
import csv
import io
from datetime import datetime
from dotenv import load_dotenv

# Načtení proměnných z .env
load_dotenv()

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
    # Inicializace schématu v PostgreSQL
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    db_connected = True
    jobs = []
    sources = []
    has_gemini_key = False
    
    try:
        # Test spojení
        db.execute(text("SELECT 1"))
        
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        sources = db.query(Source).all()
        gemini_key = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
        has_gemini_key = bool(gemini_key and gemini_key.value)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db_connected = False
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "jobs": jobs,
        "sources": sources,
        "count": len(jobs),
        "db_connected": db_connected,
        "has_gemini_key": has_gemini_key
    })

@app.post("/sources")
def add_source(url: str, name: str, db: Session = Depends(get_db)):
    try:
        new_source = Source(url=url, name=name)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source
    except Exception as e:
        db.rollback()
        logger.error(f"Chyba při přidávání zdroje: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/{source_id}")
async def run_scrape(source_id: int, db: Session = Depends(get_db)):
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source: raise HTTPException(404, detail="Zdroj nenalezen")
        
        scraped = await scrape_source(source.url, source.name)
        count = 0
        for item in scraped:
            # Kontrola duplicity
            exists = db.query(Job).filter(Job.title == item['title'], Job.source_id == source.id).first()
            if not exists:
                db.add(Job(
                    title=item['title'], 
                    company=item.get('company'), 
                    location=item.get('location'), 
                    raw_content=item.get('raw_content'), 
                    source_id=source.id
                ))
                count += 1
        
        # Aktualizace času crawl
        source.last_crawled_at = datetime.utcnow()
        db.commit()
        return {"jobs_saved": count, "jobs_found": len(scraped)}
    except Exception as e:
        db.rollback()
        logger.error(f"Chyba při scrapování: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/gemini-key")
def update_gemini_key(key: str, db: Session = Depends(get_db)):
    try:
        setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
        if setting:
            setting.value = key
        else:
            db.add(Setting(key="gemini_api_key", value=key))
        db.commit()
        return {"message": "API klíč byl uložen."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/jobs")
def export_jobs(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Company", "Location", "Keywords", "Summary", "Created At"])
    
    jobs = db.query(Job).all()
    for job in jobs:
        writer.writerow([job.id, job.title, job.company, job.location, job.keywords, job.summary, job.created_at])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=jobs_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.get("/export/sources")
def export_sources(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "URL", "Is Active"])
    
    sources = db.query(Source).all()
    for s in sources:
        writer.writerow([s.id, s.name, s.url, s.is_active])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sources_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.post("/jobs/run-ai-analysis")
def run_analysis(db: Session = Depends(get_db)):
    try:
        key_setting = db.query(Setting).filter(Setting.key == "gemini_api_key").first()
        api_key = key_setting.value if key_setting else os.getenv("GEMINI_API_KEY")
        
        unprocessed = db.query(Job).filter((Job.summary == "") | (Job.summary == None)).all()
        for job in unprocessed:
            analysis = analyze_job_with_ai(job.raw_content, api_key)
            job.keywords = analysis["keywords"]
            job.summary = f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
            job.last_analyzed_at = datetime.utcnow()
        db.commit()
        return {"message": f"Analyzováno {len(unprocessed)} pozic."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))