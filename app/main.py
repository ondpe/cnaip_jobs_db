from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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
        if templates:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "jobs": jobs,
                "sources": sources,
                "count": len(jobs)
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