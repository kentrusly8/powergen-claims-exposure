"""Match each claim to an insured plant: exact ID, then cleaned ID, then (later) plant name."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "powergen.db"
ANSWER_KEY = ROOT / "data" / "raw" / "claims_answer_key.csv"


def match_by_id(claims, exposure):
    """Tier 1: raw ID matches exactly. Tier 2: cleaned ID matches."""
    df = claims.copy()
    known = set(exposure["plant_id"])

    df["matched_plant_id"] = None
    df["match_method"] = "unmatched"

    exact = df["plant_id"].isin(known)
    df.loc[exact, "matched_plant_id"] = df.loc[exact, "plant_id"]
    df.loc[exact, "match_method"] = "exact_id"

    cleaned = ~exact & df["plant_id_clean"].isin(known)
    df.loc[cleaned, "matched_plant_id"] = df.loc[cleaned, "plant_id_clean"]
    df.loc[cleaned, "match_method"] = "clean_id"
    return df


def check_accuracy(claims):
    """Compare matches with the answer key. The matcher itself never reads this file."""
    key = pd.read_csv(ANSWER_KEY, dtype=str)
    df = claims.merge(key, on="claim_id", how="left")

    matched = df["matched_plant_id"].notna()
    correct = matched & (df["matched_plant_id"] == df["true_plant_id"])
    print("Matched:           ", matched.sum())
    print("  of which correct:", correct.sum())
    print("  of which wrong:  ", (matched & ~correct).sum())
    print("Unmatched:         ", (~matched).sum())


def main():
    conn = sqlite3.connect(DB_PATH)
    claims = pd.read_sql("SELECT * FROM clean_claims", conn)
    exposure = pd.read_sql("SELECT * FROM clean_exposure", conn)
    conn.close()

    claims = match_by_id(claims, exposure)

    print(claims["match_method"].value_counts().to_string())
    print()
    check_accuracy(claims)


if __name__ == "__main__":
    main()