"""Analyse the matched claims: loss ratio, frequency and severity by technology."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "powergen.db"


def load():
    """Read matched claims and exposure, with dates as real dates."""
    conn = sqlite3.connect(DB_PATH)
    claims = pd.read_sql("SELECT * FROM matched_claims", conn,
                         parse_dates=["loss_date_clean"])
    exposure = pd.read_sql("SELECT * FROM clean_exposure", conn,
                           parse_dates=["policy_start", "policy_end"])
    conn.close()
    return claims, exposure


def add_policy_info(claims, exposure):
    """Attach each claim's plant data, then work out net loss and whether the loss is covered."""
    cols = ["plant_id", "technology",
            "deductible_eur", "policy_start", "policy_end"]
    df = claims.merge(exposure[cols], left_on="matched_plant_id", right_on="plant_id",
                      how="inner", suffixes=("_claim", ""))

    df["net_loss_eur"] = df["amount_eur"] - df["deductible_eur"]
    df["covered"] = df["loss_date_clean"].between(
        df["policy_start"], df["policy_end"])
    return df


def main():
    claims, exposure = load()
    claims = add_policy_info(claims, exposure)

    print("Claims linked to a plant:", len(claims))
    print("Covered:                 ", claims["covered"].sum())
    print("Outside policy period:   ", (~claims["covered"]).sum())
    print(
        f"Gross losses (covered):   {claims.loc[claims['covered'], 'amount_eur'].sum():,.0f}")
    print(
        f"Net losses (covered):     {claims.loc[claims['covered'], 'net_loss_eur'].sum():,.0f}")


if __name__ == "__main__":
    main()
