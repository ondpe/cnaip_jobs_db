import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Načtení klíče z prostředí
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    logger.warning("[analyzator] GEMINI_API_KEY není nastaven, používám simulaci.")

def analyze_job_with_ai(text: str):
    """
    Analyzuje text inzerátu pomocí Gemini. 
    Pokud klíč chybí nebo API selže, vrací simulovaná data.
    """
    if model and api_key:
        try:
            prompt = f"""
            Analyzuj následující pracovní inzerát a extrahuj z něj informace v JSON formátu.
            Odpověz POUZE validním JSONem s klíči: "keywords", "seniority", "summary".
            
            - "keywords": seznam technologií a dovedností oddělený čárkou (max 10)
            - "seniority": jedna hodnota: "Junior", "Medior" nebo "Senior"
            - "summary": stručné shrnutí pozice jednou větou v češtině
            
            Inzerát:
            {text[:4000]}  # Omezení délky pro jistotu
            """
            
            response = model.generate_content(prompt)
            # Vyčištění odpovědi od případných markdown značek ```json
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(cleaned_response)
            
            return {
                "keywords": data.get("keywords", ""),
                "seniority": data.get("seniority", "Medior"),
                "summary": data.get("summary", "Analýza proběhla úspěšně.")
            }
        except Exception as e:
            logger.error(f"[analyzator] Chyba při volání Gemini API: {e}")
            # Fallback při chybě API

    # --- FALLBACK / SIMULACE (pokud není API nebo selže) ---
    tech_stack = ["Python", "JavaScript", "SQL", "Docker", "React", "AWS", "Linux", "Java", "C++"]
    found_tech = [tech for tech in tech_stack if tech.lower() in text.lower()]
    
    seniority = "Medior"
    if any(word in text.lower() for word in ["junior", "trainee", "absolvent"]):
        seniority = "Junior"
    elif "senior" in text.lower():
        seniority = "Senior"
        
    summary = f"Pozice zaměřená na {', '.join(found_tech[:2]) if found_tech else 'IT technologie'} (Simulovaná analýza)."
    
    return {
        "keywords": ", ".join(found_tech),
        "seniority": seniority,
        "summary": summary
    }