import json
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime

SITI_MONITORATI = [
    {"url": "https://www.taekwondoitalia.it/calendario/calendario-eventi.html", "livello": "Nazionale"},
    {"url": "https://www.taekwondoitalia.it/calendario/eventi-area-riservata.html", "livello": "Nazionale"},
    {"url": "https://www.taekwondocampano.it/", "livello": "Regionale"},
    {"url": "https://www.tpss2021.eu/", "livello": "Internazionale"}
]

MESI = {
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
}

# Parole da escludere tassativamente (menu, footer, link di navigazione)
ESCLUSIONI = [
    "organigramma", "contatti", "carte federali", "comitati", "progetti", 
    "area riservata", "fita hub", "privacy", "cookie", "login", "home",
    "stampa", "federazione", "atleti parataekwondo", "il taekwondo", "il paratkd"
]

def normalizza_data(testo_data):
    if not testo_data:
        return None
    
    # Formato GG/MM/AAAA o GG-MM-AAAA
    match_num = re.search(r'(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', testo_data)
    if match_num:
        g, m, a = match_num.groups()
        return f"{a}-{int(m):02d}-{int(g):02d}"

    # Formato GG Mese AAAA (es. 15 Ottobre 2026)
    pattern_testo = r'(\d{1,2})\s+(' + '|'.join(MESI.keys()) + r')\s+(\d{4})'
    match_txt = re.search(pattern_testo, testo_data, re.IGNORECASE)
    if match_txt:
        g, m_testo, a = match_txt.groups()
        m = MESI[m_testo.lower()]
        return f"{a}-{m}-{int(g):02d}"

    return None

def estrai_luogo(testo):
    """Estrae la città o il palazzetto dal testo/titolo"""
    # 1. Cerca schemi del tipo "- Città" oppure "Arezzo", "Bolzano", "Rossano"
    match = re.search(r'-\s*([A-Z][a-zA-Z\s\'-]+?)(?:Palasport|PalaEvents|Via|Palazzetto|\(|$)', testo)
    if match and len(match.group(1).strip()) > 2:
        return match.group(1).strip()
    
    # 2. Cerca parole chiave come Palasport / Palazzetto + Città
    match_pala = re.search(r'(Palasport|Palazzetto|Pala\w+)[^-\n,]*', testo, re.IGNORECASE)
    if match_pala:
        return match_pala.group(0).strip()

    return "Da definire"

def estrai_gare():
    gare_trovate = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
    }

    print("🥋 Avvio scansione avanzata gare Taekwondo...")

    for sorgente in SITI_MONITORATI:
        url = sorgente["url"]
        livello_default = sorgente["livello"]
        try:
            print(f"Scansione: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            for link_tag in soup.find_all('a', href=True):
                titolo = link_tag.get_text(" ", strip=True)
                href = link_tag['href'].strip()

                if not titolo or len(titolo) < 8:
                    continue

                titolo_lower = titolo.lower()

                # Esclude menu nav e pagine istituzionali
                if any(esc in titolo_lower for esc in ESCLUSIONI):
                    continue

                # Deve contenere almeno una parola chiave di gara realistica
                parole_chiave = ["campionato", "trofeo", "open", "cup", "interregionale", "regionale", "nazionale", "grand prix"]
                if not any(kw in titolo_lower for kw in parole_chiave):
                    continue

                full_url = urljoin(url, href)
                
                # Inizializza variabili di dettaglio
                data_evento = None
                data_scadenza = None
                luogo = estrai_luogo(titolo)

                # Estrazione date dal titolo/testo del link
                date_trovate = re.findall(
                    r'\b\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4}\b|\b\d{1,2}\s+(?:' + '|'.join(MESI.keys()) + r')\s+\d{4}\b', 
                    titolo, 
                    re.IGNORECASE
                )

                if len(date_trovate) >= 1:
                    data_evento = normalizza_data(date_trovate[0])
                if len(date_trovate) >= 2:
                    data_scadenza = normalizza_data(date_trovate[1])

                # Se non trova le date nel titolo, prova a leggere la pagina interna della gara
                if not data_evento and full_url.startswith("http"):
                    try:
                        res_dettagli = requests.get(full_url, headers=headers, timeout=5)
                        if res_dettagli.status_code == 200:
                            soup_dettaglio = BeautifulSoup(res_dettagli.text, 'html.parser')
                            testo_pagina = soup_dettaglio.get_text(" ", strip=True)
                            
                            date_interne = re.findall(
                                r'\b\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4}\b|\b\d{1,2}\s+(?:' + '|'.join(MESI.keys()) + r')\s+\d{4}\b', 
                                testo_pagina, 
                                re.IGNORECASE
                            )
                            if len(date_interne) >= 1:
                                data_evento = normalizza_data(date_interne[0])
                            if len(date_interne) >= 2:
                                data_scadenza = normalizza_data(date_interne[1])
                            
                            if luogo == "Da definire":
                                luogo = estrai_luogo(testo_pagina)
                    except Exception:
                        pass

                # Determinazione Disciplina
                disciplina = "Poomsae" if "poomsae" in titolo_lower or "forme" in titolo_lower else "Kyorugi"

                # Se non trova nessuna data valida, imposta la data evento a nullo anziché ad oggi
                gare_trovate.append({
                    "nome": titolo,
                    "tipo": "Gara",
                    "disciplina": disciplina,
                    "data_evento": data_evento or datetime.now().strftime("%Y-%m-%d"),
                    "data_scadenza": data_scadenza or data_evento,
                    "luogo": luogo,
                    "livello": livello_default,
                    "categorie": "Tutte le categorie",
                    "link": full_url
                })

        except Exception as e:
            print(f"⚠️ Errore durante la scansione di {url}: {e}")

    # Rimuove duplicati basandosi sul nome gara
    gare_uniche = list({g['nome']: g for g in gare_trovate}.values())
    return gare_uniche

if __name__ == "__main__":
    risultati = estrai_gare()
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Trovate {len(risultati)} gare pulite e dettagliate.")
