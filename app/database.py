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
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres"

if not DATABASE_URL:
    logger.error("CHYBA: Není nastavena proměnná DATABASE_URL ani DB_PASSWORD.")
    DATABASE_URL = "postgresql://user:pass@localhost/dbname"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def sync_sequences():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT setval(pg_get_serial_sequence('sources', 'id'), coalesce(max(id), 0) + 1, false) FROM sources;"))
            conn.execute(text("SELECT setval(pg_get_serial_sequence('jobs', 'id'), coalesce(max(id), 0) + 1, false) FROM jobs;"))
            conn.commit()
            logger.info("Databázové sekvence byly úspěšně synchronizovány.")
    except Exception as e:
        logger.warning(f"Synchronizace sekvencí selhala: {e}")

def fix_missing_columns():
    try:
        with engine.connect() as conn:
            # Sloupce pro sources
            conn.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_scrape_count INTEGER;"))
            conn.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_scrape_found INTEGER;"))
            # Důležité: Sloupec link pro jobs
            conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS link TEXT;"))
            conn.commit()
            logger.info("Kontrola schématu (sloupce link, statistiky) dokončena.")
    except Exception as e:
        logger.error(f"Chyba při kontrole schématu: {e}")

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        fix_missing_columns()
        sync_sequences()
        logger.info("Databázová inicializace proběhla úspěšně.")
    except Exception as e:
        logger.error(f"Inicializace databáze selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()