import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class JobScraper:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def scrape_jobs(self, url: str, source_name: str = "") -> List[Dict[str, str]]:
        logger.info(f"Startuju scraper pro: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Web vrátil chybu {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = []

            # STRATEGIE 1: Python.org (Víme přesně, co hledat)
            if "python.org" in url:
                listings = soup.find_all('h2', class_='listing-company')
                for item in listings:
                    full_text = item.get_text(strip=True)
                    jobs.append({
                        "title": full_text,
                        "company": source_name or "Python.org",
                        "location": "Remote",
                        "url": url,
                        "raw_content": full_text
                    })
            
            # STRATEGIE 2: Univerzální (Pro StartupJobs a další)
            # Pokud web neznáme, zkusíme najít všechny nadpisy, co vypadají jako práce
            else:
                # Hledáme všechny nadpisy h2 a h3, které často obsahují názvy pozic
                headers_tags = soup.find_all(['h2', 'h3'])
                for tag in headers_tags:
                    text = tag.get_text(strip=True)
                    if len(text) > 5:  # Ignorujeme příliš krátké texty
                        jobs.append({
                            "title": text,
                            "company": source_name or "Neznámá firma",
                            "location": "Dle webu",
                            "url": url,
                            "raw_content": text
                        })

            return jobs
        except Exception as e:
            logger.error(f"Scraping selhal: {e}")
            return []

async def scrape_source(url: str, source_name: str = "") -> List[Dict[str, str]]:
    async with JobScraper() as scraper:
        return await scraper.scrape_jobs(url, source_name)