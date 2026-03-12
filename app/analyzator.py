import re

def analyze_job_with_ai(text: str):
    # Simulace AI extrakce technologií
    tech_stack = ["Python", "JavaScript", "SQL", "Docker", "React", "AWS", "Linux", "Java", "C++"]
    found_tech = [tech for tech in tech_stack if tech.lower() in text.lower()]
    
    # Simulace určení seniority
    seniority = "Medior"
    if any(word in text.lower() for word in ["junior", "trainee", "absolvent"]):
        seniority = "Junior"
    elif "senior" in text.lower():
        seniority = "Senior"
        
    # Simulace shrnutí
    summary = f"Pozice zaměřená na {', '.join(found_tech[:2]) if found_tech else 'IT technologie'}."
    
    return {
        "keywords": ", ".join(found_tech),
        "seniority": seniority,
        "summary": summary
    }