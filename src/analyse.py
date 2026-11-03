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


def summary_by_technology(claims, exposure):
    """Per technology: premium, losses, frequency, severity and loss ratio."""
    exp = exposure.copy()
    exp["years"] = (
        (exp["policy_end"] - exp["policy_start"]).dt.days + 1) / 365.25
    exp["premium_eur"] = exp["annual_premium_eur"] * exp["years"]
    side_a = exp.groupby("technology").agg(plants=("plant_id", "count"),
                                           plant_years=("years", "sum"),
                                           premium_eur=("premium_eur", "sum"))

    covered = claims[claims["covered"]]
    side_b = covered.groupby("technology").agg(claims=("claim_id", "count"),
                                               net_loss_eur=("net_loss_eur", "sum"))

    df = side_a.join(side_b).fillna(0)
    df["frequency"] = df["claims"] / df["plant_years"]
    df["severity_eur"] = df["net_loss_eur"] / df["claims"]
    df["loss_ratio"] = df["net_loss_eur"] / df["premium_eur"]
    return df.sort_values("loss_ratio", ascending=False)


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

    pd.options.display.float_format = "{:,.2f}".format
    print()
    print(summary_by_technology(claims, exposure).to_string())


if __name__ == "__main__":
    main()
