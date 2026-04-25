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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
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
                        job_url = urljoin(url, title_link['href']) if (title_link and 'href' in title_link.attrs) else url
                        
                        jobs.append({
                            "title": title_text,
                            "company": source_name or "Python.org",
                            "location": "Remote",
                            "url": job_url,
                            "raw_content": title_text
                        })
            
            # STRATEGIE 2: Univerzální (Hledáme odkazy v nadpisech nebo blocku s odkazem)
            else:
                # Hledáme všechny elementy, které by mohly být nadpisem nebo odkazem na pozici
                potential_elements = soup.find_all(['h1', 'h2', 'h3', 'a'])
                
                for el in potential_elements:
                    text = el.get_text(strip=True)
                    # Ignorujeme příliš krátké texty (typicky menu)
                    if len(text) < 10:
                        continue
                    
                    # Pokud je to odkaz, zkusíme ho jako přímý link
                    if el.name == 'a' and 'href' in el.attrs:
                        job_url = urljoin(url, el['href'])
                        # Pokud link vede na jinou doménu nebo hlouběji do webu, může to být inzerát
                        if job_url != url and not any(x in job_url.lower() for x in ['login', 'register', 'privacy', 'cookie']):
                            jobs.append({
                                "title": text[:300],
                                "company": source_name or "Neznámá firma",
                                "location": "Dle webu",
                                "url": job_url,
                                "raw_content": text
                            })
                    
                    # Pokud je to nadpis, zkusíme najít odkaz uvnitř nebo v rodiči
                    elif el.name in ['h1', 'h2', 'h3']:
                        link_tag = el.find('a') or el.find_parent('a')
                        if link_tag and 'href' in link_tag.attrs:
                            job_url = urljoin(url, link_tag['href'])
                            jobs.append({
                                "title": text[:300],
                                "company": source_name or "Neznámá firma",
                                "location": "Dle webu",
                                "url": job_url,
                                "raw_content": text
                            })

            # Odstraníme duplicity v rámci jednoho scrapingu podle titulku
            unique_jobs = {}
            for j in jobs:
                if j['title'] not in unique_jobs:
                    unique_jobs[j['title']] = j
            
            return list(unique_jobs.values())
            
        except Exception as e:
            logger.error(f"Scraping selhal: {e}")
            return []

async def scrape_source(url: str, source_name: str = "") -> List[Dict[str, str]]:
    async with JobScraper() as scraper:
        return await scraper.scrape_jobs(url, source_name)