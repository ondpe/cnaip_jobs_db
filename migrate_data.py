import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Source, Job, Setting

logger = logging.getLogger(__name__)

def migrate():
    """
    Hlavní migrační funkce. Spouští se dynamicky, aby zachytila aktuální env proměnné.
    """
    SQLITE_URL = "sqlite:///./data/jobs.db"
    SUPABASE_URL = os.getenv("DATABASE_URL")

    if not SUPABASE_URL:
        msg = "CHYBA: Proměnná DATABASE_URL není v prostředí nalezena!"
        print(msg)
        raise ValueError(msg)

    # Oprava prefixu pro SQLAlchemy (Supabase dává postgres://, ale SQLAlchemy chce postgresql://)
    if SUPABASE_URL.startswith("postgres://"):
        SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql://", 1)

    print(f"--- Start migrace ---")
    print(f"Zdroj: {SQLITE_URL}")
    print(f"Cíl (Supabase): {SUPABASE_URL[:25]}...")

    try:
        # Vytvoření enginů
        sqlite_engine = create_engine(SQLITE_URL)
        supabase_engine = create_engine(SUPABASE_URL)

        # Vytvoření tabulek v cíli
        Base.metadata.create_all(bind=supabase_engine)

        # Session factory
        SqliteSession = sessionmaker(bind=sqlite_engine)
        SupabaseSession = sessionmaker(bind=supabase_engine)

        sqlite_db = SqliteSession()
        supabase_db = SupabaseSession()

        # 1. Migrace Settings
        print("Migruji nastavení...")
        settings = sqlite_db.query(Setting).all()
        for s in settings:
            if not supabase_db.query(Setting).filter(Setting.key == s.key).first():
                supabase_db.add(Setting(key=s.key, value=s.value))
        
        # 2. Migrace Sources
        print("Migruji zdroje...")
        sources = sqlite_db.query(Source).all()
        for src in sources:
            # Merge zajistí, že pokud ID existuje, update-ne se, jinak se vloží
            new_src = Source(id=src.id, url=src.url, name=src.name, is_active=src.is_active)
            supabase_db.merge(new_src)
        
        supabase_db.commit()

        # 3. Migrace Jobs
        print("Migruji pracovní pozice...")
        jobs = sqlite_db.query(Job).all()
        for j in jobs:
            new_job = Job(
                id=j.id,
                title=j.title,
                company=j.company,
                location=j.location,
                keywords=j.keywords,
                summary=j.summary,
                raw_content=j.raw_content,
                source_id=j.source_id,
                created_at=j.created_at
            )
            supabase_db.merge(new_job)

        supabase_db.commit()
        print("--- Migrace byla úspěšně dokončena! ---")
        return True

    except Exception as e:
        print(f"Kritická chyba migrace: {e}")
        if 'supabase_db' in locals(): supabase_db.rollback()
        raise e
    finally:
        if 'sqlite_db' in locals(): sqlite_db.close()
        if 'supabase_db' in locals(): supabase_db.close()

if __name__ == "__main__":
    # Umožňuje spuštění i z konzole (pokud by byla dostupná)
    try:
        migrate()
    except Exception:
        pass