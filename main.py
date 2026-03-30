import os
import re
import json
import smtplib
import hashlib
import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage

# =========================================
# COMMON HELPERS
# =========================================
def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def to_float(value):
    if value is None:
        return None
    text = clean_text(value).replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def normalize_rows(rows):
    normalized = []
    for row in rows:
        normalized.append({
            "bank": clean_text(row.get("bank", "")),
            "date": clean_text(row.get("date", "")),
            "time": clean_text(row.get("time", "")),
            "currency": clean_text(row.get("currency", "")),
            "currency_name": clean_text(row.get("currency_name", "")),
            "unit": clean_text(row.get("unit", "")),
            "cash_buy": row.get("cash_buy"),
            "non_cash_buy": row.get("non_cash_buy"),
            "sell": row.get("sell"),
        })

    normalized = sorted(
        normalized,
        key=lambda x: (
            x["bank"],
            x["date"],
            x["time"],
            x["currency"],
            x["currency_name"],
            x["unit"],
            str(x["cash_buy"]),
            str(x["non_cash_buy"]),
            str(x["sell"]),
        ),
    )
    return normalized


def hash_rows(rows):
    payload = json.dumps(normalize_rows(rows), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_state(state_file):
    path = Path(state_file)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state_file, state):
    Path(state_file).write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def save_bank_excel(bank_name, rows, output_dir="output"):
    ensure_dir(output_dir)

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = df[
        [
            "bank",
            "date",
            "time",
            "currency",
            "currency_name",
            "unit",
            "cash_buy",
            "non_cash_buy",
            "sell",
        ]
    ]

    file_name = f"{bank_name.lower()}_forex_{today_str()}.xlsx"
    file_path = Path(output_dir) / file_name
    df.to_excel(file_path, index=False)
    return str(file_path)


# =========================================
# MUKTINATH SCRAPER
# =========================================
MUKTINATH_URL = "https://muktinathbank.com.np/forex"


def fetch_muktinath():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(MUKTINATH_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    date_str = today_str()

    time_map = {}
    for a in soup.select("a[data-toggle='tab']"):
        href = a.get("href", "")
        text = clean_text(a.get_text(" ", strip=True))
        if href.startswith("#"):
            time_map[href[1:]] = text

    rows = []

    for tab in soup.select(".tab-pane"):
        tab_id = clean_text(tab.get("id"))
        rate_time = time_map.get(tab_id, tab_id or "Unknown")

        for block in tab.select(".forex-wrap"):
            h5 = block.select_one("h5")
            currency_name = clean_text(h5.get_text(" ", strip=True)) if h5 else ""

            rates = block.select(".rate")
            values = {}

            for rate in rates:
                label_el = rate.select_one("h6")
                value_el = rate.select_one("p")

                label = clean_text(label_el.get_text(" ", strip=True)).lower() if label_el else ""
                value = clean_text(value_el.get_text(" ", strip=True)) if value_el else ""

                values[label] = value

            rows.append({
                "bank": "Muktinath",
                "date": date_str,
                "time": rate_time,
                "currency": "",
                "currency_name": currency_name,
                "unit": "",
                "cash_buy": to_float(values.get("buy (cash)")),
                "non_cash_buy": to_float(values.get("buy (non-cash)")),
                "sell": to_float(values.get("sell")),
            })

    return rows


# =========================================
# JBBL SCRAPER
# =========================================
BANK_NAME = "JBBL"
DATE_VALUE = today_str()

TIME_URL = "https://jbbl-public-api.jbbl.com.np/forex-rate-time/list"
RATE_URL = "https://jbbl-public-api.jbbl.com.np/forex-rate/list"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://jbbl.com.np/forex",
}


def get_json(url, params):
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_time_list(resp_json):
    data = resp_json.get("data", {})

    if isinstance(data, dict):
        for key in ["forexRateTime", "times", "timeList", "list"]:
            if isinstance(data.get(key), list):
                return data[key]

    if isinstance(data, list):
        return data

    return []


def normalize_time_item(item):
    if isinstance(item, str):
        return item.strip()

    if isinstance(item, dict):
        for key in ["time", "label", "value", "title", "timeExact"]:
            val = item.get(key)
            if val:
                return str(val).strip()

    return None


def extract_rate_list(resp_json):
    data = resp_json.get("data", {})

    if isinstance(data, dict):
        for key in ["forexCategory", "forexRate", "forexRates", "rateList", "list"]:
            if isinstance(data.get(key), list):
                return data[key]

    if isinstance(data, list):
        return data

    return []


def build_row(item, rate_date, rate_time):
    currency_info = item.get("item", {}) if isinstance(item, dict) else {}

    return {
        "bank": BANK_NAME,
        "date": rate_date,
        "time": rate_time,
        "currency": currency_info.get("code", ""),
        "currency_name": currency_info.get("name", ""),
        "unit": item.get("unit", ""),
        "cash_buy": item.get("cash_buy", ""),
        "non_cash_buy": item.get("non_cash_buy", ""),
        "sell": item.get("sell", ""),
    }


def fetch_all_times_for_date(date_value):
    resp = get_json(TIME_URL, {"date": date_value})
    raw_times = extract_time_list(resp)

    times = []
    for item in raw_times:
        t = normalize_time_item(item)
        if t and ":" in t:
            t = t.upper().replace("AM", " AM").replace("PM", " PM").replace("  ", " ").strip()
            times.append(t)

    seen = set()
    unique_times = []
    for t in times:
        if t not in seen:
            seen.add(t)
            unique_times.append(t)

    return unique_times, resp


def fetch_rates_for_time(date_value, time_value):
    resp = get_json(RATE_URL, {"date": date_value, "time": time_value})
    data = resp.get("data", {})

    rate_date = data.get("date", date_value) if isinstance(data, dict) else date_value
    rate_time = data.get("time", time_value) if isinstance(data, dict) else time_value

    rate_list = extract_rate_list(resp)

    rows = []
    for item in rate_list:
        row = build_row(item, rate_date, rate_time)
        if row["currency"]:
            rows.append(row)

    return rows


def fetch_jbbl():
    times, _ = fetch_all_times_for_date(DATE_VALUE)

    all_rows = []
    for t in times:
        rows = fetch_rates_for_time(DATE_VALUE, t)
        all_rows.extend(rows)

    return all_rows


# =========================================
# EMAIL
# =========================================
def send_email_with_attachment(subject, body, attachment_paths):
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    email_from = os.environ["EMAIL_FROM"]
    email_to = os.environ["EMAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(body)

    for file_path in attachment_paths:
        path = Path(file_path)
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name
        )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# =========================================
# MAIN
# =========================================
def main():
    state_file = "state/last_state.json"
    ensure_dir("state")
    ensure_dir("output")

    old_state = load_state(state_file)
    new_state = dict(old_state)

    bank_fetchers = {
        "Muktinath": fetch_muktinath,
        "JBBL": fetch_jbbl,
    }

    changed_files = []
    changed_banks = []

    for bank_name, fetcher in bank_fetchers.items():
        print(f"Fetching {bank_name}...")
        rows = fetcher()

        current_hash = hash_rows(rows)
        previous_hash = old_state.get(bank_name, "")

        if current_hash != previous_hash:
            print(f"New update found for {bank_name}")
            file_path = save_bank_excel(bank_name, rows, output_dir="output")
            if file_path:
                changed_files.append(file_path)
                changed_banks.append(bank_name)
            new_state[bank_name] = current_hash
        else:
            print(f"No update found for {bank_name}")

    if changed_files:
        subject = f"Forex update found - {', '.join(changed_banks)} - {today_str()}"
        body = (
            "Forex data update detected for:\n"
            + "\n".join(f"- {b}" for b in changed_banks)
            + "\n\nAttached: latest Excel file(s)."
        )
        send_email_with_attachment(subject, body, changed_files)
        print("Email sent.")
    else:
        print("No bank updates found. No email sent.")

    save_state(state_file, new_state)
    print("State saved.")


if __name__ == "__main__":
    main()
