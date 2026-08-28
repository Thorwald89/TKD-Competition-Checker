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

def normalizza_data(testo_data):
    """Converte date in testo (es. 15 Ottobre 2026 o 15/10/2026) in formato YYYY-MM-DD"""
    if not testo_data:
        return None
    
    # Cerca formato GG/MM/AAAA
    match_num = re.search(r'(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', testo_data)
    if match_num:
        g, m, a = match_num.groups()
        return f"{a}-{int(m):02d}-{int(g):02d}"

    # Cerca formato GG Mese AAAA
    pattern_testo = r'(\d{1,2})\s+(' + '|'.join(MESI.keys()) + r')\s+(\d{4})'
    match_txt = re.search(pattern_testo, testo_data, re.IGNORECASE)
    if match_txt:
        g, m_testo, a = match_txt.groups()
        m = MESI[m_testo.lower()]
        return f"{a}-{m}-{int(g):02d}"

    return None

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

            # Cerca blocchi o righe di tabelle/articoli
            elementi = soup.find_all(['tr', 'article', 'div', 'li'])

            for el in elementi:
                testo_completo = el.get_text(" ", strip=True)
                link_tag = el.find('a', href=True)
                
                if not link_tag:
                    continue

                titolo = link_tag.get_text(strip=True) or link_tag.get('title', '')
                href = link_tag['href'].strip()

                parole_chiave = ["campionato", "trofeo", "open", "cup", "gara", "fita", "taekwondo"]
                if not any(kw in testo_completo.lower() for kw in parole_chiave) or len(titolo) < 5:
                    continue

                full_url = urljoin(url, href)

                # 1. Parsing Date
                date_trovate = re.findall(r'\b\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4}\b|\b\d{1,2}\s+(?:' + '|'.join(MESI.keys()) + r')\s+\d{4}\b', testo_completo, re.IGNORECASE)
                
                data_evento = normalizza_data(date_trovate[0]) if len(date_trovate) > 0 else datetime.now().strftime("%Y-%m-%d")
                data_scadenza = normalizza_data(date_trovate[1]) if len(date_trovate) > 1 else None

                # 2. Determinazione Disciplina
                disciplina = "Poomsae" if "poomsae" in testo_completo.lower() or "forme" in testo_completo.lower() else "Kyorugi"

                # 3. Estrazione Luogo (Ricerca euristica di città italiane o parole "Palasport/Pala")
                luogo = "Da definire"
                match_luogo = re.search(r'(?:Pala\w+|Palazzetto|presso|a)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', testo_completo)
                if match_luogo:
                    luogo = match_luogo.group(0)

                gare_trovate.append({
                    "nome": titolo,
                    "tipo": "Gara",
                    "disciplina": disciplina,
                    "data_evento": data_evento,
                    "data_scadenza": data_scadenza,
                    "luogo": luogo,
                    "livello": livello_default,
                    "categorie": "Tutte le categorie",
                    "link": full_url
                })

        except Exception as e:
            print(f"⚠️ Errore durante la scansione di {url}: {e}")

    # Rimuove duplicati in base al nome della gara
    gare_uniche = list({g['nome']: g for g in gare_trovate}.values())
    return gare_uniche

if __name__ == "__main__":
    risultati = estrai_gare()
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Trovate {len(risultati)} gare strutturate correttamente.")
