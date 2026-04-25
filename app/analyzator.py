import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

last_logs = []

def add_debug_log(msg):
    global last_logs
    timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', None, None))
    log_entry = f"[{timestamp}] {msg}"
    last_logs.append(log_entry)
    if len(last_logs) > 50:
        last_logs.pop(0)
    logger.info(f"[AI DEBUG] {msg}")

def analyze_job_with_ai(text: str, api_key: str = None, model_name: str = "gemini-1.5-flash"):
    """
    Analyzuje text inzerátu pomocí Gemini.
    """
    if not text or len(text.strip()) < 25:
        return {"is_job": False, "summary": "Příliš krátký text."}

    if not api_key:
        add_debug_log("CHYBA: API klíč nebyl předán!")
        return {"is_job": True, "summary": "Chybí API klíč."}

    try:
        add_debug_log(f"Volám {model_name} pro text délky {len(text)}")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
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
        add_debug_log(f"AI analýza hotova (model: {model_name}). is_job={data.get('is_job')}")
        return {
            "is_job": data.get("is_job", True),
            "keywords": data.get("keywords", ""),
            "seniority": data.get("seniority", "Medior"),
            "summary": data.get("summary", "Pozice v oblasti AI.")
        }
    except Exception as e:
        add_debug_log(f"KRITICKÁ CHYBA GEMINI ({model_name}): {str(e)}")
        return {"is_job": True, "summary": f"Chyba AI ({model_name}): {str(e)}"}