import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# 1. Recupera la chiave API di Gemini dalle variabili d'ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente!")

client = genai.Client(api_key=GEMINI_API_KEY)

# 2. URL target (Esempio: pagina calendario o gare)
# Sostituisci questo URL con la pagina specifica da monitorare
URL_TARGET = "https://www.taekwondoitalia.it/gare.html" 

def fetch_page_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Puliamo l'HTML estraendo solo il testo visibile per risparmiare token
    soup = BeautifulSoup(response.text, "html.parser")
    # Rimuoviamo tag non utili come script e stili
    for element in soup(["script", "style", "nav", "footer"]):
        element.extract()
        
    return soup.get_text(separator=" ", strip=True)

def parse_events_with_gemini(raw_text):
    prompt = f"""
    Analizza il seguente testo estratto da un sito web di Taekwondo ed estrai tutte le gare, tornei o eventi sportivi menzionati.
    
    Restituisci unicamente un array JSON di oggetti dove ogni oggetto ha questo schema:
    - nome_evento: (stringa) Nome della gara
    - data_inizio: (stringa, formato YYYY-MM-DD se disponibile o testo)
    - data_fine: (stringa, formato YYYY-MM-DD o uguale a data_inizio)
    - luogo: (stringa) Città/Palazzetto
    - specialita: (stringa es. Combattimento, Forme, Parataekwondo, Tutti)
    - link_bando: (stringa o null se presente)

    Testo da analizzare:
    {raw_text[:12000]} # Limitiamo i caratteri per sicurezza
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    return response.text

if __name__ == "__main__":
    print("🤖 Avvio scraping della pagina...")
    try:
        text_content = fetch_page_text(URL_TARGET)
        print("📄 Testo estratto con successo. Analisi AI in corso...")
        
        events_json_str = parse_events_with_gemini(text_content)
        events_data = json.loads(events_json_str)
        
        print("\n✅ Risultati estratti dall'Agente AI:")
        print(json.dumps(events_data, indent=2, ensure_ascii=False))
        
        # Salviamo il risultato su file
        with open("gare_trovate.json", "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {e}")
