from pathlib import Path
from src.load_data import load_folder_csv
from src.preprocess import clean_floorsheet, clean_shareprice
from src.feature_engineering import build_floorsheet_features, merge_with_shareprice
from src.train_model import train_model
from src.predict import make_predictions

def main():
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(parents=True, exist_ok=True)

    floorsheet_raw = load_folder_csv("data/floorsheet")
    shareprice_raw = load_folder_csv("data/shareprice")

    floorsheet = clean_floorsheet(floorsheet_raw)
    shareprice = clean_shareprice(shareprice_raw)

    floor_features = build_floorsheet_features(floorsheet)
    merged = merge_with_shareprice(floor_features, shareprice)

    floor_features.to_csv("data/processed/floorsheet_features.csv", index=False)
    merged.to_csv("data/processed/merged_data.csv", index=False)

    mae = train_model(merged, model_path="models/stock_model.pkl")
    print(f"Model trained. MAE: {mae:.4f}")

    predictions = make_predictions(merged, model_path="models/stock_model.pkl")
    predictions.to_csv("data/processed/predictions.csv", index=False)
    print("Predictions saved to data/processed/predictions.csv")

if __name__ == "__main__":
    main()
