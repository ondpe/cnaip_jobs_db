import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Source, Job, Setting

# Konfigurace zdrojové (SQLite) a cílové (Supabase) databáze
SQLITE_URL = "sqlite:///./data/jobs.db"
SUPABASE_URL = os.getenv("DATABASE_URL")

if not SUPABASE_URL:
    print("CHYBA: Proměnná DATABASE_URL není nastavena!")
    exit(1)

if SUPABASE_URL.startswith("postgres://"):
    SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"--- Migrace dat ---")
print(f"Zdroj: {SQLITE_URL}")
print(f"Cíl: {SUPABASE_URL}")

# Vytvoření enginů a relací
sqlite_engine = create_engine(SQLITE_URL)
supabase_engine = create_engine(SUPABASE_URL)

# Vytvoření tabulek v cílové databázi, pokud neexistují
print("Vytvářím tabulky v Supabase...")
Base.metadata.create_all(bind=supabase_engine)

# Session factory
SqliteSession = sessionmaker(bind=sqlite_engine)
SupabaseSession = sessionmaker(bind=supabase_engine)

def migrate():
    sqlite_db = SqliteSession()
    supabase_db = SupabaseSession()

    try:
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
            if not supabase_db.query(Source).filter(Source.id == src.id).first():
                # Použijeme merge nebo vytvoříme nový objekt, abychom zachovali ID
                new_src = Source(id=src.id, url=src.url, name=src.name, is_active=src.is_active)
                supabase_db.merge(new_src)
        
        supabase_db.commit() # Commitneme zdroje nejdřív kvůli cizím klíčům

        # 3. Migrace Jobs
        print("Migruji pracovní pozice...")
        jobs = sqlite_db.query(Job).all()
        for j in jobs:
            if not supabase_db.query(Job).filter(Job.id == j.id).first():
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

    except Exception as e:
        print(f"Chyba během migrace: {e}")
        supabase_db.rollback()
    finally:
        sqlite_db.close()
        supabase_db.close()

if __name__ == "__main__":
    migrate()