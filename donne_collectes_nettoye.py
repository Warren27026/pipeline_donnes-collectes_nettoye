# signals.py
import os
import pandas as pd
from datetime import datetime

DATA_FOLDER = "data"

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les indicateurs techniques nécessaires :
    - rsi
    - lower_bb, upper_bb
    - macd, signal_line
    """
    import ta  # on importe ici pour éviter les erreurs si non utilisé ailleurs

    df = df.copy()

    # S'assurer que les données sont triées par date si la colonne existe
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    close = df["Close"]

    # Bandes de Bollinger (20 jours)
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["upper_bb"] = bb.bollinger_hband()
    df["lower_bb"] = bb.bollinger_lband()

    # RSI (14 jours)
    df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # MACD
    macd_ind = ta.trend.MACD(close)
    df["macd"] = macd_ind.macd()
    df["signal_line"] = macd_ind.macd_signal()

    # On supprime les premières lignes qui ont des NaN (début des indicateurs)
    df = df.dropna().reset_index(drop=True)
    return df


def generate_signals():
    """
    Lit ALL_YFINANCE.csv, calcule les indicateurs, génère un signal par symbol,
    sauvegarde latest_signals.csv + signals_history.csv et affiche un tableau.
    """
    all_path = os.path.join(DATA_FOLDER, "ALL_YFINANCE.csv")
    if not os.path.exists(all_path):
        raise FileNotFoundError(f"Fichier introuvable : {all_path}")

    all_df = pd.read_csv(all_path)
    signals = []

    # On garantit le bon format de la date
    if "date" in all_df.columns:
        all_df["date"] = pd.to_datetime(all_df["date"])

    # Boucle sur chaque symbole
    for symbol in all_df["symbol"].unique():
        df = all_df[all_df["symbol"] == symbol].copy()

        # On demande un minimum d'historique pour que les indicateurs soient stables
        if len(df) < 60:
            continue

        # Ajout des indicateurs techniques
        df = add_indicators(df)

        if len(df) < 2:
            continue

        # Dernier jour et jour précédent
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # ---- Règles BUY / SELL (au moins 2 conditions sur 3) ----

        # Conditions BUY
        cond_rsi_buy = last["rsi"] < 30
        cond_bb_buy = last["Close"] < last["lower_bb"]
        cond_macd_buy = (last["macd"] > last["signal_line"]) and (prev["macd"] <= prev["signal_line"])
        buy_count = sum([cond_rsi_buy, cond_bb_buy, cond_macd_buy])

        # Conditions SELL
        cond_rsi_sell = last["rsi"] > 70
        cond_bb_sell = last["Close"] > last["upper_bb"]
        cond_macd_sell = (last["macd"] < last["signal_line"]) and (prev["macd"] >= prev["signal_line"])
        sell_count = sum([cond_rsi_sell, cond_bb_sell, cond_macd_sell])

        if buy_count >= 2:
            signal = "BUY"
        elif sell_count >= 2:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Position par rapport aux bandes
        if last["Close"] < last["lower_bb"]:
            bb_position = "BELOW"
        elif last["Close"] > last["upper_bb"]:
            bb_position = "ABOVE"
        else:
            bb_position = "INSIDE"

        # Histogramme MACD (différence entre MACD et signal_line)
        macd_hist = last["macd"] - last["signal_line"]

        signals.append({
            "symbol": symbol,
            "date": last["date"].strftime("%Y-%m-%d") if isinstance(last["date"], pd.Timestamp) else last["date"],
            "close": round(last["Close"], 2),
            "rsi": round(last["rsi"], 2),
            "bb_position": bb_position,
            "macd_hist": round(macd_hist, 4),
            "recommendation": signal
        })

    # DataFrame des signaux du jour
    signals_df = pd.DataFrame(signals)

    # Sauvegarde des signaux du jour
    latest_path = os.path.join(DATA_FOLDER, "latest_signals.csv")
    signals_df.to_csv(latest_path, index=False)

    # Sauvegarde dans l'historique
    history_path = os.path.join(DATA_FOLDER, "signals_history.csv")
    if os.path.exists(history_path):
        history_df = pd.read_csv(history_path)
        signals_df = pd.concat([history_df, signals_df], ignore_index=True)

    signals_df.to_csv(history_path, index=False)

    # Affichage
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"\n=== SIGNAUX DU JOUR ({today_str}) ===")
    try:
        print(signals_df.to_markdown(index=False))
    except Exception:
        print(signals_df)


def main():
    generate_signals()


if __name__ == "__main__":
    main()
