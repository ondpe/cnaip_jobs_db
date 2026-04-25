import os
import logging
from sqlalchemy import create_engine, text
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
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres"

if not DATABASE_URL:
    logger.error("CHYBA: Není nastavena proměnná DATABASE_URL ani DB_PASSWORD.")
    DATABASE_URL = "postgresql://user:pass@localhost/dbname"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def sync_sequences():
    """Opravuje sekvence ID v PostgreSQL, pokud jsou rozsynchronizované."""
    try:
        with engine.connect() as conn:
            # Resetování sekvencí pro hlavní tabulky
            conn.execute(text("SELECT setval(pg_get_serial_sequence('sources', 'id'), coalesce(max(id), 0) + 1, false) FROM sources;"))
            conn.execute(text("SELECT setval(pg_get_serial_sequence('jobs', 'id'), coalesce(max(id), 0) + 1, false) FROM jobs;"))
            conn.commit()
            logger.info("Databázové sekvence byly úspěšně synchronizovány.")
    except Exception as e:
        logger.warning(f"Synchronizace sekvencí selhala (možná není Postgres): {e}")

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        sync_sequences()
        logger.info("Databázové schéma bylo inicializováno a sekvence opraveny.")
    except Exception as e:
        logger.error(f"Inicializace databáze selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()