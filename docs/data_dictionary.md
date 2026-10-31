# Data dictionary

All data in this project is synthetic. Plant names, IDs and amounts are fictional.

## How the tables connect

- `exposure`: one row per insured plant. What could be lost.
- `claims`: one row per loss event. What was actually lost.
- `plant_id` links a claim to its plant. In the raw claims data this link is often missing or inconsistent, which is the problem this project solves.

## Key terms

| Term | Meaning |
|---|---|
| Exposure | The insured assets and their values |
| Claim | A request for payment after a loss |
| Sum insured | Maximum amount payable for one plant |
| Deductible | Part of each loss the client pays themselves |
| Premium | What the client pays for insurance cover |
| Loss ratio | Claims ÷ premium. Above 100 % means losses exceeded premium income |

## Table: exposure

One row = one insured plant. This is the reference list.

| Column | Type | Meaning | Example |
|---|---|---|---|
| plant_id | text | Unique plant code, format PG-0000 | PG-0012 |
| plant_name | text | Fictional plant name | Sonnfeld Solar Park |
| country | text | Two-letter country code | DE |
| technology | text | Solar PV, Onshore Wind, Offshore Wind, Gas, Hydro, Battery Storage | Solar PV |
| capacity | number | Plant size, in the unit given in `capacity_unit` | 45 |
| capacity_unit | text | kW or MW | MW |
| commissioning_year | integer | Year the plant started operating | 2015 |
| sum_insured_eur | number | Maximum amount payable, in EUR | 38000000 |
| deductible_eur | number | Client's own share of each loss, in EUR | 250000 |
| annual_premium_eur | number | Premium per year, in EUR | 120000 |
| policy_start | date | First day of cover (YYYY-MM-DD) | 2023-01-01 |
| policy_end | date | Last day of cover (YYYY-MM-DD) | 2025-12-31 |

## Table: claims

One row = one loss event, as reported.

| Column | Type | Meaning | Example |
|---|---|---|---|
| claim_id | text | Unique claim code | CL-00045 |
| plant_id | text | Link to `exposure.plant_id` | PG-0012 |
| plant_name | text | Plant name as reported | Sonfeld Solar Park |
| technology | text | Technology as reported | PV |
| loss_date | text | Date the damage happened | 14.06.2023 |
| cause | text | Fire, Storm, Hail, Flood, Machinery breakdown, Battery thermal event | Hail |
| claim_amount | text | Amount of the loss, in `currency` | 1.250.000,00 |
| currency | text | EUR or USD | EUR |

## Built-in data problems

The raw data contains these problems on purpose, to reflect real-world data quality.

**exposure**
- Some capacities are given in kW instead of MW.

**claims**
- `plant_id` is missing on some claims, so they must be matched by name.
- `plant_id` appears in different formats: `PG-0012`, `pg12`, `PG 12`.
- Some `plant_id` values point to plants that are not in the exposure table.
- `plant_name` contains typos and inconsistent capitalisation.
- Some claims appear twice (duplicates).
- `technology` labels vary: `PV`, `Solar`, `solar pv`.
- `loss_date` uses mixed formats: `2023-06-14`, `14.06.2023`, `14 Jun 2023`. Ambiguous formats such as `06/05/2023` are avoided.
- Some loss dates fall outside the plant's policy period.
- `claim_amount` is stored as text, mixing German (`1.250.000,00`) and English (`1,250,000.00`) number formats.
- Some amounts are in USD instead of EUR.