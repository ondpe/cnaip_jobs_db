from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import os

# Database URL - prioritně bere environment proměnnou (Supabase), jinak fallback na SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jobs.db")

# Oprava pro Heroku/Supabase (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
engine = create_engine(
    DATABASE_URL,
    # connect_args jen pro SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    # V Supabase doporučujeme vytvořit tabulky přes SQL editor, 
    # ale SQLAlchemy se o to pokusí i zde při startu.
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()