import json
import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Lista dei target da scansionare
SITI_MONITORATI = [
    "https://www.taekwondoitalia.it/calendario/calendario-eventi.html",
    "https://www.taekwondoitalia.it/calendario/eventi-area-riservata.html",
    "https://www.taekwondocampano.it/",
    "https://www.tpss2021.eu/"
]

def estrai_gare():
    gare_trovate = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    print("🥋 Avvio scansione siti Taekwondo...")

    for url in SITI_MONITORATI:
        try:
            print(f"Scansione di: {url}")
            response = requests.get(url, headers=headers, timeout=15, verify=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    testo = link.get_text(strip=True)
                    href = link['href'].strip()
                    
                    if not testo or not href or href.startswith("javascript:") or href.startswith("#"):
                        continue
                    
                    # Filtra i link che contengono parole chiave legate a gare/campionati
                    parole_chiave = ["campionato", "trofeo", "open", "cup", "gara", "fita", "taekwondo", "iscrizioni", "risultati"]
                    
                    if any(kw in testo.lower() for kw in parole_chiave) or any(kw in href.lower() for kw in parole_chiave):
                        # Ricostruisce URL completo usando urljoin
                        full_url = urljoin(url, href)
                        
                        gare_trovate.append({
                            "titolo": testo,
                            "link": full_url,
                            "sorgente": url
                        })
            else:
                print(f"⚠️ Risposta {response.status_code} per URL: {url}")
                
        except Exception as e:
            print(f"⚠️ Errore durante la scansione di {url}: {e}")

    # Rimuove eventuali duplicati basati sul link
    gare_uniche = list({g['link']: g for g in gare_trovate}.values())
    return gare_uniche

if __name__ == "__main__":
    risultati = estrai_gare()
    
    # Salva il file gare_trovate.json
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Trovate {len(risultati)} gare/eventi correlati.")
    print(f"💾 File '{nome_file}' salvato con successo.")
