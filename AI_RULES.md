# AI Development Rules - Job Scraper API

## Tech Stack
*   **Backend Framework**: FastAPI for high-performance REST API and web routing.
*   **Database ORM**: SQLAlchemy for database models and abstraction.
*   **Database Engine**: SQLite (default) for local storage in the `./data/` directory.
*   **Web Scraping**: `requests` and `BeautifulSoup4` for light scraping; `Playwright` for Javascript-heavy sites.
*   **Frontend**: Jinja2 templates with Bootstrap 5 (CDN) for the dashboard UI.
*   **Data Processing**: Pandas and OpenPyXL for Excel/CSV imports and exports.
*   **AI Integration**: OpenAI API (simulated in `analyzator.py`) for job content extraction and categorization.
*   **Deployment**: Docker and Docker Compose for containerized environment management.

## Library Usage Rules
*   **API**: Use FastAPI's dependency injection (`Depends`) for database sessions and configuration.
*   **Database**: Always use SQLAlchemy models in `app/models.py`. Do not write raw SQL queries.
*   **Scraping**: Implement new scraping logic in `app/scraper.py`. Prefer `requests` for speed, but switch to `Playwright` if the content is dynamically loaded.
*   **AI/Analysis**: Centralize all LLM-related logic in `app/analyzator.py`. Always provide fallback/mock logic if the API key is missing.
*   **Templates**: Use Jinja2 in the `templates/` directory. Keep the dashboard simple and responsive using Bootstrap.
*   **Logging**: Use the standard `logging` library instead of `print()` statements for better debugging in Docker.

## Architecture Guidelines
*   **Separation of Concerns**: Keep business logic out of `main.py`. Routes go in `main.py`, models in `models.py`, scraping logic in `scraper.py`, and AI logic in `analyzator.py`.
*   **Database Initialization**: Run `Base.metadata.create_all` during the FastAPI `startup` event.
*   **Error Handling**: Return appropriate HTTP exceptions (`HTTPException`) with clear error messages for the frontend.
*   **Excel Imports**: Validate column names ('url', 'name') before processing Excel data with Pandas.