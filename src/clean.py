"""Clean the raw tables: convert text to proper types and fix inconsistent values."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "powergen.db"
USD_PER_EUR = 1.10  # same fixed rate the generator used (synthetic assumption)


def parse_amount(text):
    """Turn '1.250.000,00', '1,250,000.00' or '1250000' into 1250000.0."""
    text = text.strip()
    if text == "":
        return None

    last_comma = text.rfind(",")
    last_dot = text.rfind(".")

    if last_comma > last_dot:      # German: comma is the decimal mark
        text = text.replace(".", "").replace(",", ".")
    # English or plain: dot (or nothing) is the decimal mark
    else:
        text = text.replace(",", "")
    return float(text)


def clean_amounts(claims):
    """Add amount_eur: the claim amount as a number, always in EUR."""
    df = claims.copy()
    df["amount_eur"] = df["claim_amount"].apply(parse_amount)

    is_usd = df["currency"] == "USD"
    df.loc[is_usd, "amount_eur"] = df.loc[is_usd, "amount_eur"] / USD_PER_EUR
    df["amount_eur"] = df["amount_eur"].round(2)
    return df


def main():
    conn = sqlite3.connect(DB_PATH)
    claims = pd.read_sql("SELECT * FROM raw_claims", conn)
    conn.close()

    claims = clean_amounts(claims)

    # Checks
    print(claims[["claim_amount", "currency", "amount_eur"]
                 ].sample(8, random_state=1).to_string())
    print()
    print("Rows:           ", len(claims))
    print("USD rows:       ", (claims["currency"] == "USD").sum())
    print("Missing amounts:", claims["amount_eur"].isna().sum())
    print(f"Smallest:        {claims['amount_eur'].min():,.2f}")
    print(f"Largest:         {claims['amount_eur'].max():,.2f}")


if __name__ == "__main__":
    main()
