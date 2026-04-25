from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import logging
from typing import List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db, get_db
from app.models import Source, Job, Setting
from app.scraper import scrape_source
from app.analyzator import analyze_job_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Scraper API")

# CORS konfigurace
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

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

# --- API ENDPOINTY ---

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return jobs

@app.get("/api/sources")
def get_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()

@app.post("/api/admin/sources", dependencies=[Depends(authenticate_admin)])
def add_source(url: str, name: str, db: Session = Depends(get_db)):
    new_source = Source(url=url, name=name)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

# --- SERVÍROVÁNÍ FRONTENDU ---

frontend_dist = os.path.join(os.getcwd(), "frontend", "dist")
assets_path = os.path.join(frontend_dist, "assets")

# Pokud existuje složka s asety, namontujeme ji
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend nebyl nalezen. Klikněte na 'Rebuild' pro sestavení aplikace."}

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Ignorujeme API požadavky, ty už jsou definovány výše
    if full_path.startswith("api"):
        raise HTTPException(status_code=404)
        
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Fallback pro Vue router (SPA)
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    raise HTTPException(status_code=404)