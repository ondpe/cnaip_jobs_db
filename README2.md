



Tento projekt slouží k automatizovanému sběru pracovních nabídek z kariérních stránek, jejich následné analýze pomocí AI (LLM) a přehlednému zobrazení na webovém dashboardu.



Klíčové funkce

\- Multi-source scraping: Podpora specifických webů (Python.org) i univerzální strategie pro ostatní weby.

\- AI Anotace: Automatická extrakce technologií, seniority a shrnutí inzerátu.

\- Excel Import\*\*: Možnost hromadného nahrání zdrojových URL přes .xlsx soubor.

\- Web Dashboard: Přehledné (simple) rozhraní s vyhledáváním a filtrováním.

viz mail



\## Jak spustit projekt (Local Setup)



Pokud si projekt stahujete poprvé, postupujte podle těchto kroků:



1\. \*\*Klonování repozitáře:\*\*

&#x20;  ```bash

&#x20;  git clone <url repozitare>

&#x20;  cd job-scraper-projekt



python -m venv venv

.\\venv\\Scripts\\Activate.ps1



pip install -r requirements.txt



uvicorn app.main:app --reload



Aplikace bude dostupná na: http://127.0.0.1:8000/

