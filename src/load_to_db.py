"""Load the raw CSV files into a SQLite database.

The database file is not stored in Git. Run this script to rebuild it.
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "powergen.db"


def main():
    # Read every column as text, so the raw data is stored exactly as it arrived.
    exposure = pd.read_csv(RAW_DIR / "exposure.csv", dtype=str, keep_default_na=False)
    claims = pd.read_csv(RAW_DIR / "claims.csv", dtype=str, keep_default_na=False)

    conn = sqlite3.connect(DB_PATH)
    exposure.to_sql("raw_exposure", conn, if_exists="replace", index=False)
    claims.to_sql("raw_claims", conn, if_exists="replace", index=False)

    # Quick check: count the rows in each table
    for table in ["raw_exposure", "raw_claims"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")

    conn.close()
    print(f"Database written to {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
    