import os
import json
import logging

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

def is_likely_job(title: str, url: str, api_key: str = None, model_name: str = "gemini-1.5-flash") -> bool:
    """Rychlá kontrola, zda titulek a URL vypadají jako inzerát práce."""
    if not api_key or not title:
        return True # Pokud není klíč, raději pustíme dál
    
    import google.generativeai as genai
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(model_name)
        
        # Velmi stručný prompt pro rychlost
        prompt = f"Rozhodni, zda titulek '{title}' (URL: {url}) vypadá jako konkrétní IT pracovní inzerát. Vrať pouze slovo YES nebo NO."
        
        response = model.generate_content(prompt)
        res_text = response.text.strip().upper()
        
        is_job = "YES" in res_text
        if not is_job:
            add_debug_log(f"Filtrace: Zahozen nerelevantní odkaz '{title}'")
        return is_job
    except Exception as e:
        add_debug_log(f"Chyba při rychlé filtraci: {e}")
        return True

def analyze_job_with_ai(text: str, api_key: str = None, model_name: str = "gemini-1.5-flash"):
    """Analyzuje text inzerátu pomocí Gemini."""
    if not text or len(text.strip()) < 25:
        return {"is_job": False, "summary": "Příliš krátký text."}

    if not api_key:
        add_debug_log("CHYBA: API klíč nebyl předán!")
        return {"is_job": True, "summary": "Chybí API klíč."}

    import google.generativeai as genai
    try:
        clean_key = api_key.strip()
        add_debug_log(f"Volám {model_name} pro text délky {len(text)}")
        genai.configure(api_key=clean_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Jsi expert na nábor v IT. Analyzuj text a rozhodni, zda jde o konkrétní pracovní inzerát.
        Vrať striktně pouze JSON s těmito klíči:
        is_job: boolean (false pokud je to navigace, cookies, patička, seznam odkazů jako '76 nabídek', nebo obecné info o firmě).
        keywords: 5 klíčových technologií jako string oddělený čárkou (např. "Python, SQL, AWS").
        seniority: Junior, Medior nebo Senior (jedno slovo).
        summary: 2-3 věty česky o náplni práce, technologiích a benefitech.
        
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
        
        raw_keywords = data.get("keywords", "")
        clean_keywords = raw_keywords.replace('[', '').replace(']', '').replace('{', '').replace('}', '').strip()
        
        add_debug_log(f"AI analýza hotova (model: {model_name}). is_job={data.get('is_job')}")
        return {
            "is_job": data.get("is_job", True),
            "keywords": clean_keywords,
            "seniority": data.get("seniority", "Medior"),
            "summary": data.get("summary", "Pozice v oblasti AI.")
        }
    except Exception as e:
        add_debug_log(f"KRITICKÁ CHYBA GEMINI ({model_name}): {str(e)}")
        return {"is_job": True, "summary": f"Chyba AI ({model_name}): {str(e)}"}