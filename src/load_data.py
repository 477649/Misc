from pathlib import Path
import pandas as pd
import re

def extract_date(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None

def load_folder_csv(folder_path):
    files = sorted(Path(folder_path).glob("*.csv"))
    all_data = []

    for file in files:
        df = pd.read_csv(file)
        df["Date"] = extract_date(file.name)
        all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)
