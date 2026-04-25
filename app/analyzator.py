import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def analyze_job_with_ai(text: str, api_key: str = None):
    """
    Analyzuje text inzerátu pomocí Gemini s předaným klíčem.
    """
    if api_key and len(api_key) > 5:
        try:
            logger.info("[analyzator] Inicializuji Gemini model...")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Analyzuj pracovní inzerát a vrať striktně pouze JSON (klíče: keywords, seniority, summary).
            Keywords: seznam 5 nejdůležitějších technologií oddělených čárkou.
            Seniority: Junior/Medior/Senior. 
            Summary: jedna výstižná věta česky o obsahu práce.
            
            Inzerát:
            {text[:4000]}
            """
            
            response = model.generate_content(prompt)
            # Vyčištění textu od markdownu
            cleaned = response.text.strip().replace('```json', '').replace('```', '')
            
            # Pokus o vyhledání JSONu, pokud by Gemini vrátila i jiný text
            if '{' in cleaned:
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                cleaned = cleaned[start:end]
            
            data = json.loads(cleaned)
            logger.info(f"[analyzator] Analýza úspěšná: {data.get('seniority')}")
            
            return {
                "keywords": data.get("keywords", ""),
                "seniority": data.get("seniority", "Medior"),
                "summary": data.get("summary", "Pozice v oblasti AI a vývoje.")
            }
        except Exception as e:
            logger.error(f"[analyzator] Chyba při volání AI: {e}")

    # Fallback pokud není klíč nebo volání selže
    return {
        "keywords": "Python, AI, SQL",
        "seniority": "Medior",
        "summary": "Analýza čeká na platný API klíč."
    }