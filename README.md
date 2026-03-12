# Job Scraper API

A FastAPI-based web scraper for collecting and managing job postings.

## Features

- FastAPI REST API
- SQLAlchemy ORM with SQLite database
- Docker support for easy deployment
- Web scraping with Playwright and BeautifulSoup4
- Data export capabilities with Pandas and OpenPyXL
- OpenAI integration ready

## Project Structure

```
job-scraper/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   └── database.py      # Database configuration
├── data/                # SQLite database storage (created on first run)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

### Using Docker (Recommended)

```bash
docker compose up
```

The API will be available at `http://localhost:8000`

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the application
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /` - Root endpoint with API information
- `GET /sources` - List all job sources
- `GET /jobs` - List all scraped jobs (with optional limit parameter)
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)

## Database Schema

### Sources Table
- `id` - Primary key
- `url` - Source URL
- `name` - Source name
- `is_active` - Active status flag

### Jobs Table
- `id` - Primary key
- `title` - Job title
- `company` - Company name
- `location` - Job location
- `keywords` - Comma-separated keywords
- `summary` - Job summary
- `raw_content` - Raw scraped content
- `source_id` - Foreign key to sources
- `created_at` - Timestamp

## Next Steps

1. Implement scraping logic in a new `scraper.py` module
2. Add endpoints for creating/updating sources
3. Add job scraping triggers
4. Implement data export functionality
5. Add OpenAI integration for job analysis