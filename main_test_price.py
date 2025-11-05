# main_test_price.py
import yfinance as yf
import polars as pl

INPUT_FILE = "positions.csv"

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

def test_prices():
    print("📊 Test des prix depuis yfinance…")
    try:
        df = pl.read_csv(INPUT_FILE, separator=";")
    except Exception as e:
        print(f"❌ Impossible de lire le CSV : {e}")
        return

    for row in df.iter_rows(named=True):
        name = row.get("name")
        isin_code = row.get("isin", "")
        if not isin_code:
            print(f"⚠️ Pas de ticker défini pour {name}")
            continue

        price = get_current_price(isin_code)
        if price:
            print(f"✅ {name} : cours actuel = {price} €")
        else:
            print(f"❌ {name} : prix introuvable")

if __name__ == "__main__":
    test_prices()
