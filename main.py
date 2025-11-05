import requests
import pandas as pd
from tqdm import tqdm
from secrets import API_KEY, PROMPT_ANALYSE  # ← import direct

API_URL = "https://api.perplexity.ai/chat/completions"
INPUT_FILE = "portefeuille.csv"
OUTPUT_FILE = "rapport_portefeuille.csv"


def analyse_titre(ticker, poids):
    """Appelle l’API Perplexity pour générer un rapport sur une action donnée."""
    prompt = PROMPT_ANALYSE.format(ticker=ticker)

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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        return "⚠️ Erreur : délai d’attente dépassé."
    except requests.exceptions.HTTPError as e:
        return f"❌ Erreur HTTP : {e}"
    except Exception as e:
        return f"⚠️ Erreur inattendue : {e}"


def main():
    """Génère un rapport d’analyse pour chaque ligne du portefeuille."""
    print("📊 Chargement du portefeuille...")
    df = pd.read_csv(INPUT_FILE)

    rapports = []
    print(f"🧠 Génération du rapport pour {len(df)} titres :")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Analyse en cours", ncols=100):
        ticker = row["Ticker"]
        poids = row["Poids"]
        rapport = analyse_titre(ticker, poids)
        rapports.append({"Ticker": ticker, "Poids": poids, "Rapport": rapport})

    # Sauvegarde dans un fichier CSV
    rapport_df = pd.DataFrame(rapports)
    rapport_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"\n✅ Rapport complet enregistré dans : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
