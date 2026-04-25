import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    db_pass = os.getenv("DB_PASSWORD")
    if db_pass:
        # Používáme Transaction Pooler (port 6543) pro Supabase, což je vhodnější pro serverless
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres?sslmode=require"

if not DATABASE_URL:
    logger.error("CHYBA: Není nastavena proměnná DATABASE_URL ani DB_PASSWORD.")
    # Fallback na lokalni sqlite jen pro vyvoj, v produkci selze
    DATABASE_URL = "sqlite:///./jobs.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Přidání pool_pre_ping pro automatické obnovení spojení po timeoutu (časté u Vercelu)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def sync_sequences():
    try:
        with engine.connect() as conn:
            # Synchronizace ID sekvencí po importech nebo manuálních změnách
            conn.execute(text("SELECT setval(pg_get_serial_sequence('sources', 'id'), coalesce(max(id), 0) + 1, false) FROM sources;"))
            conn.execute(text("SELECT setval(pg_get_serial_sequence('jobs', 'id'), coalesce(max(id), 0) + 1, false) FROM jobs;"))
            conn.commit()
            logger.info("Databázové sekvence byly úspěšně synchronizovány.")
    except Exception as e:
        logger.warning(f"Synchronizace sekvencí selhala: {e}")

def fix_missing_columns():
    try:
        with engine.connect() as conn:
            # Sloupce pro sources (statistiky)
            conn.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_scrape_count INTEGER;"))
            conn.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_scrape_found INTEGER;"))
            
            # Sloupce pro jobs (odkaz a surový obsah)
            conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS link TEXT;"))
            conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS raw_content TEXT;"))
            
            conn.commit()
            logger.info("Kontrola schématu (sloupce link, raw_content, statistiky) dokončena.")
    except Exception as e:
        logger.error(f"Chyba při kontrole schématu: {e}")

def init_db():
    try:
        # Metadata create_all vytvoří tabulky pokud neexistují
        Base.metadata.create_all(bind=engine)
        # Fix missing columns zajistí, že existují i sloupce přidané později
        fix_missing_columns()
        # Sync sequences zajistí správné generování ID
        sync_sequences()
        logger.info("Databázová inicializace proběhla úspěšně.")
    except Exception as e:
        logger.error(f"Inicializace databáze selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()