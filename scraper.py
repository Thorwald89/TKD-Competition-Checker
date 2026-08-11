import json
import os
import requests
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("🥋 Avvio scansione siti Taekwondo...")

    for url in SITI_MONITORATI:
        try:
            print(f"Scansione di: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Esempio di ricerca generica per tag e titoli gare
                # (Questa logica verrà affinata via via in base ai selettori specifici)
                for link in soup.find_all('a', href=True):
                    testo = link.get_text(strip=True)
                    href = link['href']
                    
                    # Filtra i link che contengono parole chiave legate a gare/campionati
                    if any(kw in testo.lower() for kw in ["campionato", "trofeo", "open", "cup", "gara", "fita"]):
                        if not href.startswith("http"):
                            # Ricostruisce URL relativo
                            base_url = "/".join(url.split("/")[:3])
                            href = base_url + href if href.startswith("/") else url + "/" + href
                            
                        gare_trovate.append({
                            "titolo": testo,
                            "link": href,
                            "sorgente": url
                        })
        except Exception as e:
            print(f"⚠️ Errore durante la scansione di {url}: {e}")

    # Rimuove eventuali duplicati basati sul link
    gare_uniche = {g['link']: g for g in gare_trovate}.values()
    return list(gare_uniche)

if __name__ == "__main__":
    risultati = estrai_gare()
    
    # Salva SEMPRE il file gare_trovate.json per evitare il warning di GitHub Actions
    nome_file = "gare_trovate.json"
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=4)
        
    print(f" Trovate {len(risultati)} gare/eventi correlati.")
    print(f" File '{nome_file}' salvato con successo.")
