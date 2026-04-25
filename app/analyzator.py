import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def analyze_job_with_ai(text: str, api_key: str = None):
    """
    Analyzuje text inzerátu pomocí Gemini. 
    Pokud klíč chybí, vrací informaci o simulaci.
    """
    # Rychlá heuristika pro zjevný odpad (krátké texty)
    if not text or len(text.strip()) < 25:
        return {
            "is_job": False,
            "keywords": "",
            "seniority": "",
            "summary": "Příliš krátký text pro inzerát."
        }

    if api_key and len(api_key) > 5:
        try:
            logger.info(f"[analyzator] Volám Gemini pro text délky {len(text)}")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Jsi expert na nábor v IT. Analyzuj text a rozhodni, zda jde o konkrétní pracovní inzerát.
            Vrať striktně pouze JSON s těmito klíči:
            is_job: boolean (false pokud je to navigace, cookies, patička, seznam odkazů jako '76 nabídek', nebo obecné info o firmě).
            keywords: 5 klíčových technologií (pokud is_job=true).
            seniority: Junior/Medior/Senior (pokud is_job=true).
            summary: jedna věta česky o náplni práce (pokud is_job=true).
            
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
            return {
                "is_job": data.get("is_job", True),
                "keywords": data.get("keywords", ""),
                "seniority": data.get("seniority", "Medior"),
                "summary": data.get("summary", "Pozice v oblasti AI.")
            }
        except Exception as e:
            logger.error(f"[analyzator] Chyba Gemini: {e}")

    # Fallback při chybě nebo chybějícím klíči
    return {
        "is_job": True,
        "keywords": "Python, SQL",
        "seniority": "Nezjištěno",
        "summary": "Čeká na AI analýzu (klíč nebyl nalezen)."
    }