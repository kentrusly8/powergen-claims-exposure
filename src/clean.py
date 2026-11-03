"""Clean the raw tables: convert text to proper types and fix inconsistent values."""

import re
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


DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y", "%d %b %Y"]


def clean_dates(claims):
    """Add loss_date_clean: the loss date as a real date, whatever format it came in."""
    df = claims.copy()
    parsed = pd.Series(pd.NaT, index=df.index)
    for fmt in DATE_FORMATS:
        attempt = pd.to_datetime(df["loss_date"], format=fmt, errors="coerce")
        parsed = parsed.fillna(attempt)
    df["loss_date_clean"] = parsed
    return df


TECH_MAP = {
    "solar pv": "Solar PV", "pv": "Solar PV", "solar": "Solar PV",
    "onshore wind": "Onshore Wind", "wind onshore": "Onshore Wind",
    "offshore wind": "Offshore Wind", "wind offshore": "Offshore Wind", "offshore": "Offshore Wind",
    "gas": "Gas", "gas turbine": "Gas", "ccgt": "Gas",
    "hydro": "Hydro", "hydropower": "Hydro",
    "battery storage": "Battery Storage", "bess": "Battery Storage", "battery": "Battery Storage",
}


def clean_technology(claims):
    """Add technology_clean: one of the 6 standard technology names."""
    df = claims.copy()
    key = df["technology"].str.strip().str.lower()
    df["technology_clean"] = key.map(TECH_MAP)
    return df


def normalise_id(text):
    """Turn 'pg12', 'PG 12' or 'PG-0012' into 'PG-0012'. Empty stays empty."""
    digits = re.sub(r"\D", "", text)
    if digits == "":
        return None
    return f"PG-{int(digits):04d}"


def clean_plant_ids(claims):
    """Add plant_id_clean: the plant ID in the standard 'PG-0000' format."""
    df = claims.copy()
    df["plant_id_clean"] = df["plant_id"].apply(normalise_id)
    return df


def remove_duplicates(claims):
    """Drop rows that are exact copies of another row (the same claim entered twice)."""
    return claims.drop_duplicates().reset_index(drop=True)


def clean_exposure(exposure):
    """Convert text columns to numbers and dates, and give every capacity in MW."""
    df = exposure.copy()

    capacity = df["capacity"].astype(float)
    in_kw = df["capacity_unit"] == "kW"
    capacity[in_kw] = capacity[in_kw] / 1000
    df["capacity_mw"] = capacity.round(1)

    for col in ["sum_insured_eur", "deductible_eur", "annual_premium_eur"]:
        df[col] = df[col].astype(float)
    df["commissioning_year"] = df["commissioning_year"].astype(int)
    df["policy_start"] = pd.to_datetime(df["policy_start"])
    df["policy_end"] = pd.to_datetime(df["policy_end"])
    return df


def main():
    conn = sqlite3.connect(DB_PATH)
    claims = pd.read_sql("SELECT * FROM raw_claims", conn)
    exposure = pd.read_sql("SELECT * FROM raw_exposure", conn)
    conn.close()

    # Clean claims
    rows_before = len(claims)
    claims = remove_duplicates(claims)
    claims = clean_amounts(claims)
    claims = clean_dates(claims)
    claims = clean_technology(claims)
    claims = clean_plant_ids(claims)

    # Clean exposure
    exposure = clean_exposure(exposure)

    # Save
    conn = sqlite3.connect(DB_PATH)
    claims.to_sql("clean_claims", conn, if_exists="replace", index=False)
    exposure.to_sql("clean_exposure", conn, if_exists="replace", index=False)
    for table in ["clean_claims", "clean_exposure"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Saved {table}: {count} rows")
    conn.close()
    print()

    # Checks
    print(claims[["claim_amount", "currency", "amount_eur"]
                 ].sample(8, random_state=1).to_string())

    print()
    print("Rows:           ", len(claims))
    print("USD rows:       ", (claims["currency"] == "USD").sum())
    print("Missing amounts:", claims["amount_eur"].isna().sum())
    print(f"Smallest:        {claims['amount_eur'].min():,.2f}")
    print(f"Largest:         {claims['amount_eur'].max():,.2f}")

    print()
    print(claims[["loss_date", "loss_date_clean"]].sample(
        6, random_state=2).to_string())
    print("Missing dates:  ", claims["loss_date_clean"].isna().sum())
    print("Earliest:       ", claims["loss_date_clean"].min().date())
    print("Latest:         ", claims["loss_date_clean"].max().date())

    print()
    print(claims["technology_clean"].value_counts().to_string())
    unmapped = claims.loc[claims["technology_clean"].isna(),
                          "technology"].unique()
    print("Unmapped labels:", list(unmapped))

    print()
    reformatted = claims["plant_id"].ne("") & (
        claims["plant_id"] != claims["plant_id_clean"])
    print(claims.loc[reformatted, ["plant_id",
          "plant_id_clean"]].head(6).to_string())
    print("Reformatted IDs:", reformatted.sum())
    print("Missing IDs:    ", claims["plant_id_clean"].isna().sum())

    print()
    print("Duplicates removed:", rows_before - len(claims))
    print("Rows left:         ", len(claims))
    print("Claim IDs unique:  ", claims["claim_id"].is_unique)

    print()
    print("Plants:     ", len(exposure))
    print("kW rows:    ", (exposure["capacity_unit"] == "kW").sum())
    print(exposure.groupby("technology")[
          "capacity_mw"].agg(["min", "max"]).to_string())


if __name__ == "__main__":
    main()
