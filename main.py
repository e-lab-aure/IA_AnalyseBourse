# main.py
import os
import polars as pl
import requests
from fpdf import FPDF
from tqdm import tqdm
import yfinance as yf
from secrets_variables import API_KEY, PROMPT_ANALYSE  # <-- changement ici

INPUT_FILE = "positions.csv"
OUTPUT_DIR = "RAPPORTS"
ARIAL_FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
API_URL = "https://api.perplexity.ai/chat/completions"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_current_price(isin_code: str):
    """Récupère le dernier prix de clôture d’une action via yfinance."""
    try:
        ticker = yf.Ticker(isin_code)
        data = ticker.history(period="1d")
        if not data.empty:
            return data["Close"].iloc[-1]
        else:
            print(f"⚠️ Aucun historique pour {isin_code}")
    except Exception as e:
        print(f"⚠️ Impossible de récupérer le prix pour {isin_code}: {e}")
    return None

def call_perplexity(prompt: str) -> tuple[str, list[str]]:
    """Appel à l’API Perplexity pour générer un rapport et récupérer les sources."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        sources = [s.get("link", "") for s in data.get("sources", [])] if "sources" in data else []
        return answer, sources
    except requests.exceptions.Timeout:
        return "⚠️ Erreur : délai d’attente dépassé.", []
    except requests.exceptions.HTTPError as e:
        return f"❌ Erreur HTTP : {e}", []
    except Exception as e:
        return f"⚠️ Erreur inattendue : {e}", []

def generate_pdf(name: str, isin: str, rapport: str, current_price: float, sources: list):
    """Génère un PDF avec UTF-8 et Arial Unicode dans RAPPORTS."""
    if not os.path.isfile(ARIAL_FONT_PATH):
        raise FileNotFoundError(f"Police Arial non trouvée : {ARIAL_FONT_PATH}")

    safe_name = name.replace(" ", "_").replace("/", "_")
    filename = os.path.join(OUTPUT_DIR, f"rapport_{safe_name}_{isin}.pdf")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("ArialUnicode", "", ARIAL_FONT_PATH, uni=True)

    pdf.set_font("ArialUnicode", '', 16)
    pdf.cell(0, 10, f"Rapport : {name}", ln=True)
    pdf.ln(5)
    pdf.set_font("ArialUnicode", '', 12)
    pdf.multi_cell(0, 6, f"Cours actuel : {current_price if current_price else 'N/A'} €\n\n{rapport}")
    pdf.ln(5)
    if sources:
        pdf.set_font("ArialUnicode", 'B', 12)
        pdf.cell(0, 6, "Sources & citations :", ln=True)
        pdf.set_font("ArialUnicode", '', 10)
        for src in sources:
            pdf.multi_cell(0, 6, src)

    pdf.output(filename)
    print(f"📄 PDF généré : {filename}")

def main():
    print("📊 Chargement du portefeuille...")
    try:
        df = pl.read_csv(INPUT_FILE, separator=";")
    except Exception as e:
        print(f"❌ Impossible de lire le fichier CSV : {e}")
        return

    # Phase 1 : afficher tous les prix
    prices = {}
    print("\n💰 Prix actuels récupérés via yfinance :")
    for row in df.iter_rows(named=True):
        name = row.get("name")
        isin_code = row.get("isin", "")
        if not name or not isin_code:
            continue
        price = get_current_price(isin_code)
        prices[isin_code] = price
        print(f"{name} ({isin_code}) : {price if price else 'N/A'} €")

    # Confirmation avant d'appeler Perplexity
    proceed = input("\nVoulez-vous lancer l'analyse Perplexity et générer les PDF ? (oui/non) : ").strip().lower()
    if proceed != "oui":
        print("❌ Analyse interrompue par l'utilisateur.")
        return

    # Phase 2 : génération des rapports
    print(f"\n🧠 Génération des rapports pour {len(df)} titres :")
    for row in tqdm(df.iter_rows(named=True), total=len(df), desc="Analyse en cours", ncols=100):
        name = row.get('name')
        isin_code = row.get('isin', '')
        current_price = prices.get(isin_code)

        if not name or not isin_code:
            continue

        if current_price is None:
            print(f"⚠️ Prix introuvable pour {name} ({isin_code}), saut de l’analyse.")
            continue

        prompt = PROMPT_ANALYSE.format(name=name, isin=isin_code)
        prompt += f"\nLe cours actuel de l’action est de {current_price} €."

        print(f"\n🔎 Analyse de {name} ({isin_code}) …")
        rapport, sources = call_perplexity(prompt)
        generate_pdf(name, isin_code, rapport, current_price, sources)

    print("\n✅ Tous les rapports ont été générés.")

if __name__ == "__main__":
    main()
