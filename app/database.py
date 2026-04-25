import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.models import Base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    db_pass = os.getenv("DB_PASSWORD")
    if db_pass:
        # Port 6543 je pro Supabase Connection Pooler (Transaction mode)
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres?sslmode=require&pgbouncer=true"

if not DATABASE_URL:
    logger.warning("Není nastavena proměnná DATABASE_URL ani DB_PASSWORD. Používám lokální SQLite (jobs.db).")
    DATABASE_URL = "sqlite:///./jobs.db"

# SQLAlchemy vyžaduje prefix postgresql:// místo postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool if "postgresql" in DATABASE_URL else None,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Databázová inicializace proběhla úspěšně.")
    except Exception as e:
        logger.error(f"Inicializace databáze selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()