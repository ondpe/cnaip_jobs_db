import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def analyze_job_with_ai(text: str, api_key: str = None):
    """
    Analyzuje text inzerátu pomocí Gemini. 
    Vrací také příznak 'is_job', který určuje, zda jde o validní inzerát.
    """
    if api_key and len(api_key) > 5:
        try:
            logger.info("[analyzator] Inicializuji Gemini model...")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Analyzuj text a rozhodni, zda jde o konkrétní pracovní inzerát (nabídku práce).
            Vrať striktně pouze JSON s těmito klíči:
            is_job: boolean (true pokud je to inzerát, false pokud je to jiný text jako patička, cookies, obecné info).
            keywords: seznam 5 nejdůležitějších technologií oddělených čárkou (pokud is_job=true).
            seniority: Junior/Medior/Senior (pokud is_job=true).
            summary: jedna výstižná věta česky o obsahu práce (pokud is_job=true).
            
            Text k analýze:
            {text[:4000]}
            """
            
            response = model.generate_content(prompt)
            cleaned = response.text.strip().replace('```json', '').replace('```', '')
            
            if '{' in cleaned:
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                cleaned = cleaned[start:end]
            
            data = json.loads(cleaned)
            logger.info(f"[analyzator] Analýza hotova. Is job: {data.get('is_job')}")
            
            return {
                "is_job": data.get("is_job", True),
                "keywords": data.get("keywords", ""),
                "seniority": data.get("seniority", "Medior"),
                "summary": data.get("summary", "Pozice v oblasti AI a vývoje.")
            }
        except Exception as e:
            logger.error(f"[analyzator] Chyba při volání AI: {e}")

    # Fallback
    return {
        "is_job": True,
        "keywords": "Python, AI, SQL",
        "seniority": "Medior",
        "summary": "Analýza čeká na platný API klíč."
    }