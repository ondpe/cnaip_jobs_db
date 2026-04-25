import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.models import Base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Zkusíme načíst URL z různých možných proměnných
DATABASE_URL = os.getenv("DATABASE_URL")
DB_PASS_ENV = os.getenv("DB_PASSWORD")

# Pokud DB_PASSWORD obsahuje celé URL, použijeme ho jako základ
if DB_PASS_ENV and (DB_PASS_ENV.startswith("postgres://") or DB_PASS_ENV.startswith("postgresql://")):
    DATABASE_URL = DB_PASS_ENV
elif not DATABASE_URL and DB_PASS_ENV:
    # Pokud máme jen heslo, sestavíme URL s Transactional Poolerem (port 6543)
    # Všimněte si uživatelského jména 'postgres.aoslyffxsmktzsrjakrb', které Supabase vyžaduje u nového pooleru
    DATABASE_URL = f"postgresql://postgres.aoslyffxsmktzsrjakrb:{DB_PASS_ENV}@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&supavisor_session_id=true"

if not DATABASE_URL:
    logger.warning("Není nastavena proměnná DATABASE_URL ani DB_PASSWORD. Používám lokální SQLite (jobs.db).")
    DATABASE_URL = "sqlite:///./jobs.db"

# SQLAlchemy vyžaduje prefix postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Pro Vercel (serverless) je klíčové použít NullPool, aby nedocházelo k vyčerpání spojení
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