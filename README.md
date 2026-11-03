# PowerGen Claims–Exposure Matcher

Linking insurance claims to the insured assets they belong to, for a synthetic
portfolio of power generation plants.

> **Synthetic data only.** Every plant, policy and claim in this repository is
> randomly generated. Nothing here describes a real asset, client, insurer or company.

## The problem

Property insurance portfolios are described by two datasets:

- **Exposure data**: what is insured. Each plant, its technology, capacity,
  sum insured and premium.
- **Claims data**: what was lost. Each claim's date, cause and amount.

The two are often kept in separate systems. Identifiers go missing or change
format, names are misspelled, and amounts, dates and units are recorded
inconsistently. Until each claim is linked to the right asset, core underwriting
measures such as loss ratio, claim frequency and claim severity by technology
cannot be calculated reliably.

## How it works

```
generate_data.py → load_to_db.py → clean.py → match.py → analyse.py → app.py
  synthetic CSVs     raw_ tables    clean_ tables  matched_claims  report   web app
```

1. **Generate** a synthetic portfolio of 120 plants across six technologies, with claims
   that contain deliberate data-quality problems (missing or reformatted IDs, typos,
   mixed date and number formats, USD amounts, duplicates, unknown plants).
2. **Load** the raw files into SQLite exactly as received, every column as text.
3. **Clean** amounts, dates, technology labels and plant IDs; remove duplicates;
   convert units. Clean values are added next to the raw ones, never over them.
4. **Match** each claim to a plant in three tiers: exact ID, normalised ID, then
   name similarity within the same technology (threshold 0.90). Claims that cannot be
   matched go to a review queue. Accuracy is measured against an answer key that the
   matcher never reads.
5. **Analyse** net loss after deductible, whether each loss falls inside its policy
   period, and frequency, severity and loss ratio by technology, including the effect
   of the largest losses.
6. **Explore** the results in a Streamlit app: portfolio overview, plant lookup and
   review queue.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/run_pipeline.py   # rebuilds data and database from scratch
streamlit run src/app.py     # opens the app in the browser
```

The data generator uses a fixed random seed, so every run produces identical results.

## Project structure

```
data/raw/        generated CSVs: exposure, claims and the matching answer key
docs/            data dictionary
sql/             exploratory SQL queries on the raw tables
src/
  generate_data.py   synthetic portfolio and messy claims
  load_to_db.py      raw CSVs → SQLite
  clean.py           raw tables → clean tables
  match.py           clean claims → matched claims
  analyse.py         loss ratio, frequency, severity, largest losses
  app.py             Streamlit app
  run_pipeline.py    runs all steps in order
```

The SQLite database (`data/powergen.db`) is not stored in the repository; the
pipeline rebuilds it.
