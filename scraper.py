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

# Parole chiave che indicano una pagina di navigazione o istituzionale da ignorare
URL_DA_ESCLUDERE = [
    "organigramma", "contatti", "carte-federali", "comitati", "progetti", 
    "area-riservata", "fita-hub", "privacy", "cookie", "login", "home",
    "stampa", "federazione", "paratkd", "taekwondo-italia", "statuto",
    "regolamenti", "storia", "societa", "quadri-federali", "verbali"
]

def normalizza_data(testo_data):
    if not testo_data:
        return None
    match_num = re.search(r'(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', testo_data)
    if match_num:
        g, m, a = match_num.groups()
        return f"{a}-{int(m):02d}-{int(g):02d}"

    pattern_testo = r'(\d{1,2})\s+(' + '|'.join(MESI.keys()) + r')\s+(\d{4})'
    match_txt = re.search(pattern_testo, testo_data, re.IGNORECASE)
    if match_txt:
        g, m_testo, a = match_txt.groups()
        m = MESI[m_testo.lower()]
        return f"{a}-{m}-{int(g):02d}"

    return None

def estrai_luogo(testo):
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

    print("🥋 Avvio scansione mirata gare Taekwondo...")

    for sorgente in SITI_MONITORATI:
        url = sorgente["url"]
        livello_default = sorgente["livello"]
        try:
            print(f"Scansione: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # --- ISOLAMENTO CONTENUTO PRINCIPALE ---
            # Rimuove menu, footer, header e barre laterali dall'HTML prima dell'analisi
            for elemento_inutile in soup.find_all(['nav', 'header', 'footer', 'aside', '.menu', '.nav', '.footer']):
                elemento_inutile.decompose()

            # Cerca il blocco principale (main, content, article o body pulito)
            main_content = soup.find('main') or soup.find('div', id=re.compile(r'content|main|articolo', re.I)) or soup.body

            if not main_content:
                continue

            for link_tag in main_content.find_all('a', href=True):
                titolo = link_tag.get_text(" ", strip=True)
                href = link_tag['href'].strip()
                full_url = urljoin(url, href)

                if not titolo or len(titolo) < 10:
                    continue

                titolo_lower = titolo.lower()
                url_lower = full_url.lower()

                # 1. Filtro URL: Se l'URL o il testo contiene parole di menu, salta subito
                if any(esc in url_lower or esc in titolo_lower for esc in URL_DA_ESCLUDERE):
                    continue

                # 2. Requisito minimo: Il titolo o l'URL devono contenere parole chiave reali di gare
                parole_evento = ["campionato", "trofeo", "open", "cup", "interregionale", "regionale", "nazionale", "grand prix", "gara", "torneo"]
                if not any(pe in titolo_lower or pe in url_lower for pe in parole_evento):
                    continue

                # Inizializzazione dati
                data_evento = None
                data_scadenza = None
                luogo = estrai_luogo(titolo)

                # Estrazione date dal testo del link o dagli elementi adiacenti (es. celle di tabella)
                testo_contesto = link_tag.find_parent(['tr', 'li', 'article', 'div'])
                testo_da_analizzare = testo_contesto.get_text(" ", strip=True) if testo_contesto else titolo

                date_trovate = re.findall(
                    r'\b\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4}\b|\b\d{1,2}\s+(?:' + '|'.join(MESI.keys()) + r')\s+\d{4}\b', 
                    testo_da_analizzare, 
                    re.IGNORECASE
                )

                if len(date_trovate) >= 1:
                    data_evento = normalizza_data(date_trovate[0])
                if len(date_trovate) >= 2:
                    data_scadenza = normalizza_data(date_trovate[1])

                disciplina = "Poomsae" if "poomsae" in titolo_lower or "forme" in titolo_lower else "Kyorugi"

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

    # Rimuove duplicati esatti basandosi sia sul nome della gara che sul link
    gare_uniche = list({(g['nome'], g['link']): g for g in gare_trovate}.values())
    return gare_uniche

if __name__ == "__main__":
    risultati = estrai_gare()
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Trovate {len(risultati)} gare reali ed escluse le pagine di sistema.")
