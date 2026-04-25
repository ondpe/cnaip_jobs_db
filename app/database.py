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
        # Port 6543 je pro Transaction Pooler v Supabase, což je pro Vercel (serverless) nejlepší volba
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres?sslmode=require"

if not DATABASE_URL:
    logger.error("CHYBA: Není nastavena proměnná DATABASE_URL ani DB_PASSWORD.")
    DATABASE_URL = "sqlite:///./jobs.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Nastavení pool_pre_ping je kritické pro Vercel, aby se předešlo chybám s "odpojeným" socketem
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 10}
)
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
        logger.warning(f"Synchronizace sekvencí selhala (pravděpodobně tabulky ještě neexistují): {e}")

def fix_missing_columns():
    try:
        with engine.connect() as conn:
            # Postupné zajištění existence všech sloupců
            tables_cols = {
                "sources": ["last_scrape_count", "last_scrape_found"],
                "jobs": ["link", "raw_content"]
            }
            for table, cols in tables_cols.items():
                for col in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} INTEGER;"))
                    except:
                        # Pokud selže jako INTEGER, zkusíme TEXT pro link/raw_content
                        if col in ["link", "raw_content"]:
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} TEXT;"))
            conn.commit()
            logger.info("Kontrola schématu dokončena.")
    except Exception as e:
        logger.error(f"Chyba při kontrole schématu: {e}")

def init_db():
    try:
        # Vytvoření tabulek
        Base.metadata.create_all(bind=engine)
        # Oprava schématu pro existující databáze
        fix_missing_columns()
        # Synchronizace sekvencí
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