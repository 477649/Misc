import pandas as pd

def clean_floorsheet(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Rate"] = pd.to_numeric(df["Rate"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Buyer"] = pd.to_numeric(df["Buyer"], errors="coerce")
    df["Seller"] = pd.to_numeric(df["Seller"], errors="coerce")
    df = df.dropna(subset=["Date", "Symbol", "Quantity", "Rate"])
    return df

def clean_shareprice(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()

    numeric_cols = [
        "Open", "High", "Low", "Close", "LTP",
        "Close - LTP", "Close - LTP %", "VWAP",
        "Vol", "Prev. Close", "Turnover"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Date", "Symbol", "Close"])
    return df
