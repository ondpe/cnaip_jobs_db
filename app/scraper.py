import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from urllib.parse import urljoin

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

            # STRATEGIE 1: Python.org
            if "python.org" in url:
                listings = soup.find_all('li')
                for item in listings:
                    h2 = item.find('h2', class_='listing-company')
                    if h2:
                        title_link = h2.find('a')
                        title_text = h2.get_text(strip=True)
                        job_url = urljoin(url, title_link['href']) if title_link else url
                        
                        jobs.append({
                            "title": title_text,
                            "company": source_name or "Python.org",
                            "location": "Remote",
                            "url": job_url,
                            "raw_content": title_text
                        })
            
            # STRATEGIE 2: Univerzální (Hledáme odkazy v nadpisech)
            else:
                headers_tags = soup.find_all(['h2', 'h3'])
                for tag in headers_tags:
                    text = tag.get_text(strip=True)
                    if len(text) > 5:
                        # Zkusíme najít odkaz uvnitř nebo v okolí nadpisu
                        link_tag = tag.find('a') or tag.find_parent('a')
                        job_url = urljoin(url, link_tag['href']) if (link_tag and 'href' in link_tag.attrs) else url
                        
                        jobs.append({
                            "title": text,
                            "company": source_name or "Neznámá firma",
                            "location": "Dle webu",
                            "url": job_url,
                            "raw_content": text
                        })

            return jobs
        except Exception as e:
            logger.error(f"Scraping selhal: {e}")
            return []

async def scrape_source(url: str, source_name: str = "") -> List[Dict[str, str]]:
    async with JobScraper() as scraper:
        return await scraper.scrape_jobs(url, source_name)