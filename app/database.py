import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# 1. Získání URL z prostředí
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Fallback: Sestavení URL ze známého hosta a hesla (Supabase)
if not DATABASE_URL:
    db_pass = os.getenv("DB_PASSWORD")
    if db_pass:
        # Použití Pooler portu 6543 pro lepší kompatibilitu
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres"

if not DATABASE_URL:
    logger.error("CHYBA: Není nastavena proměnná DATABASE_URL ani DB_PASSWORD. Aplikace nebude fungovat.")
    # V produkci bychom zde vyhodili chybu, pro teď necháme prázdné ať nespadne import
    DATABASE_URL = "postgresql://user:pass@localhost/dbname"

# Oprava prefixu pro SQLAlchemy (supabase vrací postgres://, SQLAlchemy vyžaduje postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Vytvoření enginu pro PostgreSQL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Databázové schématu bylo inicializováno na Supabase.")
    except Exception as e:
        logger.error(f"Inicializace databáze selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()