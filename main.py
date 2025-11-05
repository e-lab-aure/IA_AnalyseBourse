# main.py
import requests
import polars as pl
from fpdf import FPDF
from tqdm import tqdm
from secrets import API_KEY, PROMPT_ANALYSE
import os

API_URL = "https://api.perplexity.ai/chat/completions"
INPUT_FILE = "positions.csv"

# Chemin vers la police Arial Unicode sur Windows
# Par défaut sur Windows : C:\Windows\Fonts\arial.ttf
ARIAL_FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

def analyse_titre(name, isin):
    """Appelle l’API Perplexity pour générer un rapport sur une action donnée."""
    prompt = PROMPT_ANALYSE.format(name=name, isin=isin)

    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        print(f"🔹 Analyse en cours pour {name} ({isin})...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Analyse terminée pour {name}")
        return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        print(f"⚠️ Timeout pour {name}")
        return "⚠️ Erreur : délai d’attente dépassé."
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP pour {name}: {e}")
        return f"❌ Erreur HTTP : {e}"
    except Exception as e:
        print(f"⚠️ Erreur inattendue pour {name}: {e}")
        return f"⚠️ Erreur inattendue : {e}"

def generate_pdf(name, isin, rapport):
    """Génère un PDF pour un titre avec UTF-8 et Arial Unicode."""
    pdf = FPDF()
    pdf.add_page()

    if not os.path.isfile(ARIAL_FONT_PATH):
        raise FileNotFoundError(f"Police Arial non trouvée : {ARIAL_FONT_PATH}")

    # Ajouter la police Arial Unicode
    pdf.add_font("Arial", "", ARIAL_FONT_PATH, uni=True)
    pdf.set_font("Arial", '', 16)
    pdf.cell(0, 10, f"Rapport : {name}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 6, rapport)

    filename = f"rapport_{name}_{isin}.pdf"
    pdf.output(filename)
    print(f"📄 PDF généré : {filename}")

def main():
    print("📊 Chargement du portefeuille...")
    try:
        df = pl.read_csv(INPUT_FILE, separator=";", truncate_ragged_lines=True)
    except Exception as e:
        print(f"❌ Impossible de lire le CSV : {e}")
        return

    print(f"🧠 Génération du rapport pour {df.height} titres :")

    for idx, row in enumerate(tqdm(df.iter_rows(named=True), total=df.height, desc="Analyse en cours", ncols=100), start=1):
        name = row.get('name')
        isin = row.get('isin')

        if not name or not isin:
            print(f"⚠️ Ligne {idx} ignorée (champ name ou isin manquant)")
            continue

        rapport = analyse_titre(name, isin)
        generate_pdf(name, isin, rapport)

    print("\n✅ Tous les rapports ont été générés.")

if __name__ == "__main__":
    main()
