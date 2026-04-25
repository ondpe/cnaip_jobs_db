import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def analyze_job_with_ai(text: str, api_key: str = None):
    """
    Analyzuje text inzerátu pomocí Gemini s předaným klíčem.
    """
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Analyzuj pracovní inzerát a vrať JSON (klíče: keywords, seniority, summary).
            Seniority: Junior/Medior/Senior. Summary: jedna věta česky.
            
            Inzerát:
            {text[:4000]}
            """
            
            response = model.generate_content(prompt)
            cleaned = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(cleaned)
            
            return {
                "keywords": data.get("keywords", ""),
                "seniority": data.get("seniority", "Medior"),
                "summary": data.get("summary", "OK")
            }
        except Exception as e:
            logger.error(f"[analyzator] Chyba: {e}")

    # Fallback
    return {
        "keywords": "Python, SQL",
        "seniority": "Medior",
        "summary": "Simulovaná analýza (klíč nenalezen nebo chyba)."
    }