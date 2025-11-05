# main.py
import os
import re
import polars as pl
import yfinance as yf
import requests
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from secrets_variables import API_KEY, PROMPT_ANALYSE

# ====================== CONFIG ======================
INPUT_FILE = "positions.csv"
OUTPUT_DIR = "RAPPORTS"
API_URL = "https://api.perplexity.ai/chat/completions"
ARIAL_FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ====================== FONCTIONS ======================
def clean_report_text(text: str) -> str:
    """
    Nettoie le texte renvoyé par Perplexity pour l'affichage dans un PDF Arial.
    - Supprime Markdown, emojis, balises HTML et caractères non supportés.
    - Uniformise le style du texte pour un rendu lisible et professionnel.
    """
    # Supprimer les emojis et symboles non ASCII
    text = re.sub(r"[^\x00-\x7FÀ-ÿ€£¥çÇéèêëàâäîïôöùûüÉÈÊËÀÂÄÎÏÔÖÙÛÜ]", "", text)

    # Supprimer le Markdown (*, _, #, etc.)
    text = re.sub(r"[*_`#~>-]+", "", text)

    # Supprimer les liens Markdown ou HTML
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)

    # Corriger les espaces et sauts de ligne multiples
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    # Remplacer les tirets ou puces par un format lisible
    text = re.sub(r"^\s*[-–—]\s*", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"\n-\s+", "\n• ", text)

    # Nettoyage final
    return text.strip()


def get_current_price(isin_code: str):
    """Récupère le dernier prix de clôture d’une action via yfinance."""
    try:
        ticker = yf.Ticker(isin_code)
        data = ticker.history(period="1d")
        if not data.empty:
            return data["Close"].iloc[-1]
    except Exception as e:
        print(f"⚠️ Impossible de récupérer le prix pour {isin_code}: {e}")
    return None


def call_perplexity(name, isin, current_price):
    """Appelle l’API Perplexity pour générer un rapport financier complet."""
    prompt = PROMPT_ANALYSE.format(name=name, isin=isin, current_price=current_price)

    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        return f"❌ Erreur HTTP : {e}"
    except Exception as e:
        return f"⚠️ Erreur inattendue : {e}"


def generate_pdf(name, isin, rapport_text, current_price=None, sources=None):
    """Génère un PDF lisible et propre avec Arial."""
    pdf = FPDF()
    pdf.add_page()

    # Ajouter police Arial
    pdf.add_font("ArialUnicode", "", ARIAL_FONT_PATH)
    pdf.add_font("ArialUnicode", "B", ARIAL_FONT_PATH)
    pdf.add_font("ArialUnicode", "I", ARIAL_FONT_PATH)
    pdf.add_font("ArialUnicode", "BI", ARIAL_FONT_PATH)

    # Titre
    pdf.set_font("ArialUnicode", "B", 16)
    pdf.cell(0, 10, f"Rapport : {name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if current_price:
        pdf.set_font("ArialUnicode", "", 12)
        pdf.cell(0, 8, f"Cours actuel : {current_price:.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Texte principal nettoyé
    pdf.set_font("ArialUnicode", "", 12)
    pdf.multi_cell(0, 6, rapport_text)
    pdf.ln(5)

    # Sources (si fournies)
    if sources:
        pdf.set_font("ArialUnicode", "I", 10)
        pdf.multi_cell(0, 5, f"Sources : {', '.join(sources)}")

    filename = os.path.join(OUTPUT_DIR, f"rapport_{name}_{isin}.pdf")
    pdf.output(filename)
    print(f"📄 PDF généré : {filename}")


# ====================== MAIN ======================
def main():
    # Charger le portefeuille
    print("📊 Chargement du portefeuille...")
    try:
        df = pl.read_csv(INPUT_FILE, separator=";", truncate_ragged_lines=True)
    except Exception as e:
        print(f"❌ Impossible de lire le CSV : {e}")
        return

    # Afficher les prix du jour
    print("🔎 Vérification des cours actuels…")
    for row in df.iter_rows(named=True):
        name = row.get("name")
        isin = row.get("isin")
        current_price = get_current_price(isin)
        if current_price:
            print(f"✅ {name} ({isin}) : {current_price:.2f} €")
        else:
            print(f"⚠️ {name} ({isin}) : prix introuvable")

    # Confirmation avant génération
    confirm = input("Voulez-vous générer les rapports Perplexity pour tous les titres ? (o/n) : ").lower()
    if confirm != "o":
        print("❌ Annulé par l'utilisateur.")
        return

    # Génération des rapports
    for row in df.iter_rows(named=True):
        name = row.get("name")
        isin = row.get("isin")
        current_price = get_current_price(isin)
        print(f"🧠 Génération du rapport pour {name} ({isin})…")
        rapport_md = call_perplexity(name, isin, current_price)
        rapport_text = clean_report_text(rapport_md)
        generate_pdf(name, isin, rapport_text, current_price=current_price)


if __name__ == "__main__":
    main()
