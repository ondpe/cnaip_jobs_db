import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from dotenv import load_dotenv

# Zajištění načtení proměnných
load_dotenv()

# 1. Zkusíme vzít celou URL z prostředí
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Fallback: Sestavení URL ze známého hosta a hesla (Supabase)
if not DATABASE_URL:
    db_pass = os.getenv("DB_PASSWORD")
    if db_pass:
        # Použití Pooler portu 6543 pro lepší kompatibilitu (často nutné u serverless/agentů)
        DATABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:6543/postgres"

# 3. Finální fallback na lokální SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./data/jobs.db"

# Oprava prefixu pro SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Vytvoření enginu
engine_args = {}
if "sqlite" in DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()