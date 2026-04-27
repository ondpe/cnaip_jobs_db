import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("DATABASE_URL není nastavena. Používám lokální SQLite.")
    DATABASE_URL = "sqlite:///./jobs.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool if "postgresql" in DATABASE_URL else None,
    pool_pre_ping=True if "postgresql" in DATABASE_URL else False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        # Pouze ověření konektivity místo pomalého create_all
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("DB spojení OK.")
    except Exception as e:
        logger.error(f"Inicializace DB selhala: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()