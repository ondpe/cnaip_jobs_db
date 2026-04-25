# Job Scraper Pro (Supabase Edition)

Tato aplikace slouží k automatizovanému scrapování pracovních nabídek a jejich analýze pomocí AI.

## Technologie
- **Backend**: FastAPI, SQLAlchemy
- **Databáze**: Supabase (PostgreSQL)
- **AI**: Google Gemini (volitelně)
- **Scraping**: BeautifulSoup4, Playwright

## Konfigurace
Pro správný běh je nutné nastavit v souboru `.env`:
- `DB_PASSWORD`: Heslo k databázi Supabase
- `GEMINI_API_KEY`: (Volitelně) Klíč pro AI analýzu

## Spuštění
```bash
docker compose up
```
Aplikace bude dostupná na `http://localhost:8000`.