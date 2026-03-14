import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

def train_model(df, model_path="models/stock_model.pkl"):
    df = df.copy()
    df = df.sort_values(["Symbol", "Date"])

    df["Target"] = df.groupby("Symbol")["Close"].shift(-1)

    feature_cols = [
        "Open", "High", "Low", "Close", "LTP", "VWAP", "Vol", "Prev. Close", "Turnover",
        "TradeCount", "TotalQuantity", "TotalAmount", "AvgRate",
        "MaxRate", "MinRate", "UniqueBuyers", "UniqueSellers",
        "MaxTradeQty", "AvgTradeSize", "AvgAmountPerTrade",
        "QtyPerBuyer", "QtyPerSeller"
    ]

    available_features = [c for c in feature_cols if c in df.columns]
    model_df = df.dropna(subset=available_features + ["Target"]).copy()

    X = model_df[available_features]
    y = model_df["Target"]

    split_index = int(len(model_df) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)

    joblib.dump({
        "model": model,
        "features": available_features
    }, model_path)

    return mae
