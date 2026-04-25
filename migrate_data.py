import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Source, Job, Setting

logger = logging.getLogger(__name__)

def migrate():
    SQLITE_URL = "sqlite:///./data/jobs.db"
    
    # Použijeme stejnou logiku jako v database.py
    SUPABASE_URL = os.getenv("DATABASE_URL")
    if not SUPABASE_URL:
        db_pass = os.getenv("DB_PASSWORD")
        if db_pass:
            SUPABASE_URL = f"postgresql://postgres:{db_pass}@db.aoslyffxsmktzsrjakrb.supabase.co:5432/postgres"

    if not SUPABASE_URL:
        msg = "CHYBA: Nastavte DATABASE_URL nebo DB_PASSWORD v Environment Variables!"
        print(msg)
        raise ValueError(msg)

    if SUPABASE_URL.startswith("postgres://"):
        SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql://", 1)

    print(f"--- Start migrace ---")
    print(f"Zdroj: {SQLITE_URL}")
    
    try:
        sqlite_engine = create_engine(SQLITE_URL)
        supabase_engine = create_engine(SUPABASE_URL)
        Base.metadata.create_all(bind=supabase_engine)

        SqliteSession = sessionmaker(bind=sqlite_engine)
        SupabaseSession = sessionmaker(bind=supabase_engine)
        sqlite_db = SqliteSession()
        supabase_db = SupabaseSession()

        print("Migruji data...")
        # Settings
        for s in sqlite_db.query(Setting).all():
            if not supabase_db.query(Setting).filter(Setting.key == s.key).first():
                supabase_db.add(Setting(key=s.key, value=s.value))
        
        # Sources
        for src in sqlite_db.query(Source).all():
            supabase_db.merge(Source(id=src.id, url=src.url, name=src.name, is_active=src.is_active))
        
        supabase_db.commit()

        # Jobs
        for j in sqlite_db.query(Job).all():
            supabase_db.merge(Job(
                id=j.id, title=j.title, company=j.company, location=j.location,
                keywords=j.keywords, summary=j.summary, raw_content=j.raw_content,
                source_id=j.source_id, created_at=j.created_at
            ))

        supabase_db.commit()
        print("--- Migrace dokončena! ---")
        return True
    except Exception as e:
        print(f"Chyba: {e}")
        raise e
    finally:
        if 'sqlite_db' in locals(): sqlite_db.close()
        if 'supabase_db' in locals(): supabase_db.close()

if __name__ == "__main__":
    migrate()