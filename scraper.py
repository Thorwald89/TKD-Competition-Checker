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

PAROLE_OBBLIGATORIE_GARA = [
    "campionato", "campionati", "trofeo", "open", "cup", "grand prix", 
    "interregionale", "regionale", "nazionale", "gara", "torneo", "stage"
]

PAROLE_VIETATE = [
    "organigramma", "contatti", "carte federali", "comitati", "progetti", 
    "area riservata", "fita hub", "privacy", "cookie", "login", "home",
    "stampa", "federazione", "atleti parataekwondo", "il taekwondo", "il paratkd"
]

def estrai_date_da_testo(testo):
    """
    Gestisce date in formato italiano, inglese e gli intervalli tipici di TPSS
    (es. '04-09 upto 05-09, 2026', '12-09-2026', '10-11 Ottobre 2026')
    """
    if not testo:
        return None, None

    date_estratte = []

    # 1. Formato specifico TPSS con 'upto': "04-09 upto 05-09, 2026"
    match_tpss = re.search(r'(\d{1,2})[-/](\d{1,2})\s+upto\s+(\d{1,2})[-/](\d{1,2}),?\s*(\d{4})', testo, re.IGNORECASE)
    if match_tpss:
        g1, m1, g2, m2, a = match_tpss.groups()
        return f"{a}-{int(m1):02d}-{int(g1):02d}", f"{a}-{int(m2):02d}-{int(g2):02d}"

    # 2. Formati standard numerici (DD-MM-YYYY o DD/MM/YYYY)
    matches_num = re.finditer(r'(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', testo)
    for m in matches_num:
        g, m_num, a = m.groups()
        date_estratte.append(f"{a}-{int(m_num):02d}-{int(g):02d}")

    # 3. Formati con mese testuale italiano (es. 10-11 Ottobre 2026)
    pattern_mesi = '|'.join(MESI.keys())
    regex_testo = r'(\d{1,2})(?:\s*[-–\sa]\s*(\d{1,2}))?\s+(' + pattern_mesi + r')\s+(\d{4})'
    matches_txt = re.finditer(regex_testo, testo, re.IGNORECASE)

    for m in matches_txt:
        g1, g2, m_txt, a = m.groups()
        m_num = MESI[m_txt.lower()]
        date_estratte.append(f"{a}-{m_num}-{int(g1):02d}")
        if g2:
            date_estratte.append(f"{a}-{m_num}-{int(g2):02d}")

    if not date_estratte:
        return None, None

    data_inizio = date_estratte[0]
    data_fine = date_estratte[1] if len(date_estratte) > 1 else data_inizio
    return data_inizio, data_fine

def estrai_luogo(testo):
    """Estrae città o impianti sportivi dal contesto"""
    match = re.search(r'-\s*([A-Z][a-zA-Z\s\'-]+?)(?:Palasport|PalaEvents|Via|Palazzetto|\(|$)', testo)
    if match and len(match.group(1).strip()) > 2:
        return match.group(1).strip()
    
    match_pala = re.search(r'(Palasport|Palazzetto|Pala\w+)[^-\n,]*', testo, re.IGNORECASE)
    if match_pala:
        return match_pala.group(0).strip()

    return "Da definire"

def estrai_gare():
    gare_trovate = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
    }

    print("🥋 Avvio scansione con parsing avanzato date e TPSS...")

    for sorgente in SITI_MONITORATI:
        url = sorgente["url"]
        livello_default = sorgente["livello"]
        try:
            print(f"Scansione: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Rimuove menu e footer
            for el in soup.find_all(['nav', 'header', 'footer', 'aside']):
                el.decompose()

            # Analizza ogni riga/scheda di evento (tr, div, li, article)
            blocchi = soup.find_all(['tr', 'article', 'li', 'div'])

            for blocco in blocchi:
                link_tag = blocco.find('a', href=True)
                if not link_tag:
                    continue

                titolo = link_tag.get_text(" ", strip=True)
                if not titolo or len(titolo) < 6:
                    continue

                titolo_lower = titolo.lower()

                if any(v in titolo_lower for v in PAROLE_VIETATE):
                    continue

                if not any(o in titolo_lower for o in PAROLE_OBBLIGATORIE_GARA):
                    continue

                # Prende tutto il testo dell'intera riga della tabella / contenitore per trovare le date adiacenti
                testo_completo_blocco = blocco.get_text(" ", strip=True)

                data_evento, data_scadenza = estrai_date_da_testo(testo_completo_blocco)

                full_url = urljoin(url, link_tag['href'].strip())

                # Se la data non c'è nella tabella esterna, apre la scheda dettaglio per trovarla
                if not data_evento and full_url.startswith("http"):
                    try:
                        res_det = requests.get(full_url, headers=headers, timeout=4)
                        if res_det.status_code == 200:
                            soup_det = BeautifulSoup(res_det.text, 'html.parser')
                            data_evento, data_scadenza = estrai_date_da_testo(soup_det.get_text(" ", strip=True))
                    except Exception:
                        pass

                # Se non è stata estratta alcuna data valida, salta l'elemento
                if not data_evento:
                    continue

                luogo = estrai_luogo(testo_completo_blocco)
                disciplina = "Poomsae" if "poomsae" in titolo_lower or "forme" in titolo_lower else "Kyorugi"

                gare_trovate.append({
                    "nome": titolo,
                    "tipo": "Gara",
                    "disciplina": disciplina,
                    "data_evento": data_evento,
                    "data_scadenza": data_scadenza or data_evento,
                    "luogo": luogo,
                    "livello": livello_default,
                    "categorie": "Tutte le categorie",
                    "link": full_url
                })

        except Exception as e:
            print(f"⚠️ Errore durante la scansione di {url}: {e}")

    # Rimuove duplicati esatti per nome gara
    gare_uniche = list({g['nome']: g for g in gare_trovate}.values())
    return gare_uniche

if __name__ == "__main__":
    risultati = estrai_gare()
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Trovate {len(risultati)} gare con date ed estratti corretti.")
