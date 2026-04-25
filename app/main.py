from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
import os
import logging
from datetime import datetime

# Importy
from app.database import init_db, get_db
from app.models import Source, Job
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Scraper Pro")

# Pokus o načtení šablon s fallbackem
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
        # Kontrola, zda běžíme na Supabase (Postgres)
        is_supabase = "postgresql" in str(db.get_bind().url)
        
        if templates:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "jobs": jobs,
                "sources": sources,
                "count": len(jobs),
                "is_supabase": is_supabase
            })
        return HTMLResponse("<h1>Web běží!</h1><p>Šablony se nepodařilo načíst, ale API je aktivní.</p>")
    except Exception as e:
        return HTMLResponse(f"<h1>Chyba</h1><p>{str(e)}</p>")

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

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
    return {"jobs_saved": count}

@app.post("/jobs/run-ai-analysis")
def run_analysis(db: Session = Depends(get_db)):
    unprocessed = db.query(Job).filter((Job.summary == "") | (Job.summary == None)).all()
    for job in unprocessed:
        analysis = analyze_job_with_ai(job.raw_content)
        job.keywords, job.summary = analysis["keywords"], f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
    db.commit()
    return {"message": f"Analyzováno {len(unprocessed)} pozic."}

@app.post("/api/migrate-from-sqlite")
async def migrate_data(db_target: Session = Depends(get_db)):
    sqlite_path = "./data/jobs.db"
    if not os.path.exists(sqlite_path):
        return JSONResponse({"error": f"Soubor {sqlite_path} nebyl nalezen."}, status_code=404)
    
    # Připojení k původní SQLite
    engine_sqlite = create_engine(f"sqlite:///{sqlite_path}")
    SessionSQLite = sessionmaker(bind=engine_sqlite)
    db_source = SessionSQLite()
    
    try:
        # 1. Přeneseme Zdroje
        sources = db_source.query(Source).all()
        for s in sources:
            if not db_target.query(Source).filter(Source.id == s.id).first():
                db_target.add(Source(id=s.id, url=s.url, name=s.name, is_active=s.is_active))
        db_target.commit()

        # 2. Přeneseme Pozice
        jobs = db_source.query(Job).all()
        for j in jobs:
            if not db_target.query(Job).filter(Job.id == j.id).first():
                db_target.add(Job(
                    id=j.id, title=j.title, company=j.company, location=j.location,
                    keywords=j.keywords, summary=j.summary, raw_content=j.raw_content,
                    source_id=j.source_id, created_at=j.created_at
                ))
        db_target.commit()

        # 3. Reset sekvencí v Postgresu (aby ID zase fungovala od konce)
        if "postgresql" in str(db_target.get_bind().url):
            db_target.execute(text("SELECT setval('sources_id_seq', (SELECT MAX(id) FROM sources))"))
            db_target.execute(text("SELECT setval('jobs_id_seq', (SELECT MAX(id) FROM jobs))"))
            db_target.commit()

        return {"message": f"Migrace úspěšná! Přeneseno {len(sources)} zdrojů a {len(jobs)} pozic."}
    except Exception as e:
        db_target.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db_source.close()