"""Match each claim to an insured plant: exact ID, then cleaned ID, then plant name."""

import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "powergen.db"
ANSWER_KEY = ROOT / "data" / "raw" / "claims_answer_key.csv"
NAME_THRESHOLD = 0.90  # below this, a name match is too uncertain and goes to review


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


def similarity(a, b):
    """How alike two names are, from 0 (nothing alike) to 1 (identical). Ignores upper/lower case."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def match_by_name(claims, exposure):
    """Tier 3: for claims still unmatched, find the most similar plant name of the same technology."""
    df = claims.copy()
    df["name_score"] = None
    df["best_candidate"] = None

    for i in df.index[df["match_method"] == "unmatched"]:
        name = df.at[i, "plant_name"]
        candidates = exposure[exposure["technology"]
                              == df.at[i, "technology_clean"]]
        if candidates.empty:  # unknown technology: nothing to compare, leave unmatched
            continue
        scores = candidates["plant_name"].apply(
            lambda plant: similarity(name, plant))

        best = scores.idxmax()
        df.at[i, "name_score"] = round(scores[best], 3)
        df.at[i, "best_candidate"] = candidates.at[best, "plant_name"]
        if scores[best] >= NAME_THRESHOLD:
            df.at[i, "matched_plant_id"] = candidates.at[best, "plant_id"]
            df.at[i, "match_method"] = "name"
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
    claims = match_by_name(claims, exposure)

    conn = sqlite3.connect(DB_PATH)
    claims.to_sql("matched_claims", conn, if_exists="replace", index=False)
    conn.close()

    print(claims["match_method"].value_counts().to_string())
    print()
    check_accuracy(claims)

    print()
    left = claims["match_method"] == "unmatched"
    print(claims.loc[left, ["plant_id", "plant_name",
                            "best_candidate", "name_score"]].to_string())


if __name__ == "__main__":
    main()
