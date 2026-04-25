from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import logging
from datetime import datetime

# Importy z našeho projektu
from app.database import init_db, get_db
from app.models import Source, Job
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai

# Logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializace aplikace
app = FastAPI(title="Job Scraper Pro")

# Nastavení šablon - zkusíme relativní cestu k aktuálnímu pracovnímu adresáři
# Většinou je to v Dockeru/Dyadu kořen projektu
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Šablony inicializovány ze složky 'templates'")
except Exception as e:
    logger.error(f"Chyba při inicializaci šablon: {e}")

@app.on_event("startup")
def startup_event():
    # Vytvoření složky pro data pokud neexistuje
    if not os.path.exists("data"):
        os.makedirs("data")
    init_db()
    logger.info("Databáze inicializována")

# --- HLAVNÍ STRÁNKA ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    logger.info("GET /")
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
        logger.error(f"Chyba na hlavní stránce: {e}")
        return HTMLResponse(content=f"<h1>Chyba aplikace</h1><p>{str(e)}</p>", status_code=500)

# --- API ENDPOINTY ---
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
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        scraped_jobs = await scrape_source(source.url, source.name)
        new_count = 0
        for item in scraped_jobs:
            # Kontrola duplicity podle názvu
            exists = db.query(Job).filter(Job.title == item['title'], Job.source_id == source.id).first()
            if not exists:
                job = Job(
                    title=item['title'],
                    company=item.get('company', 'Unknown'),
                    location=item.get('location', 'N/A'),
                    raw_content=item.get('raw_content', ''),
                    source_id=source.id,
                    summary="",
                    keywords=""
                )
                db.add(job)
                new_count += 1
        db.commit()
        return {"jobs_found": len(scraped_jobs), "jobs_saved": new_count}
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/run-ai-analysis")
def run_analysis(db: Session = Depends(get_db)):
    unprocessed = db.query(Job).filter((Job.summary == "") | (Job.summary == None)).all()
    for job in unprocessed:
        analysis = analyze_job_with_ai(job.raw_content)
        job.keywords = analysis["keywords"]
        job.summary = f"{analysis['summary']} (Seniorita: {analysis['seniority']})"
    db.commit()
    return {"message": f"Analyzováno {len(unprocessed)} pozic."}