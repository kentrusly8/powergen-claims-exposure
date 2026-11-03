# Data dictionary

All data in this project is synthetic. Plant names, IDs and amounts are fictional.

## How the tables connect

- `exposure`: one row per insured plant. What could be lost.
- `claims`: one row per loss event. What was actually lost.
- `plant_id` links a claim to its plant. In the raw claims data this link is often missing or inconsistent, which is the problem this project solves.

## Key terms

| Term        | Meaning                                                                                                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| Exposure    | The insured assets and their values                                                                               |
| Claim       | A request for payment after a loss                                                                                |
| Sum insured | Maximum amount payable for one plant                                                                              |
| Deductible  | Part of each loss the client pays themselves                                                                      |
| Premium     | What the client pays for insurance cover                                                                          |
| Loss ratio  | Net losses (after deductible) ÷ premium earned over the policy period. Above 1 means losses exceeded premium income |

## Table: exposure

One row = one insured plant. This is the reference list.

| Column             | Type    | Meaning                                                            | Example             |
| ------------------ | ------- | ------------------------------------------------------------------ | ------------------- |
| plant_id           | text    | Unique plant code, format PG-0000                                  | PG-0012             |
| plant_name         | text    | Fictional plant name                                               | Frostham Solar Park |
| country            | text    | Two-letter country code                                            | DE                  |
| technology         | text    | Solar PV, Onshore Wind, Offshore Wind, Gas, Hydro, Battery Storage | Solar PV            |
| capacity           | number  | Plant size, in the unit given in `capacity_unit`                   | 45                  |
| capacity_unit      | text    | kW or MW                                                           | MW                  |
| commissioning_year | integer | Year the plant started operating                                   | 2015                |
| sum_insured_eur    | number  | Maximum amount payable, in EUR                                     | 38000000            |
| deductible_eur     | number  | Client's own share of each loss, in EUR                            | 250000              |
| annual_premium_eur | number  | Premium per year, in EUR                                           | 120000              |
| policy_start       | date    | First day of cover (YYYY-MM-DD)                                    | 2023-01-01          |
| policy_end         | date    | Last day of cover (YYYY-MM-DD)                                     | 2024-12-31          |

## Table: claims

One row = one loss event, as reported.

| Column       | Type | Meaning                                                              | Example            |
| ------------ | ---- | -------------------------------------------------------------------- | ------------------ |
| claim_id     | text | Unique claim code                                                    | CL-00045           |
| plant_id     | text | Link to `exposure.plant_id`                                          | PG-0012            |
| plant_name   | text | Plant name as reported                                               | Frostam Solar Park |
| technology   | text | Technology as reported                                               | PV                 |
| loss_date    | text | Date the damage happened                                             | 14.06.2023         |
| cause        | text | Fire, Storm, Hail, Flood, Machinery breakdown, Battery thermal event | Hail               |
| claim_amount | text | Amount of the loss, in `currency`                                    | 1.250.000,00       |
| currency     | text | EUR or USD                                                           | EUR                |

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

## Derived columns

Columns the pipeline adds. The raw columns are always kept next to them.

| Column           | Added by   | Meaning                                                                     | Example             |
| ---------------- | ---------- | --------------------------------------------------------------------------- | ------------------- |
| amount_eur       | clean.py   | `claim_amount` as a number, converted to EUR                                | 1250000.00          |
| loss_date_clean  | clean.py   | `loss_date` as a real date                                                  | 2023-06-14          |
| technology_clean | clean.py   | `technology` mapped to one of the 6 standard names                          | Solar PV            |
| plant_id_clean   | clean.py   | `plant_id` in the standard format PG-0000 (empty if missing)                | PG-0012             |
| capacity_mw      | clean.py   | `capacity` converted to MW (exposure table)                                 | 45.0                |
| matched_plant_id | match.py   | The plant the claim was matched to (empty if unmatched)                     | PG-0012             |
| match_method     | match.py   | How it was matched: `exact_id`, `clean_id`, `name` or `unmatched`           | name                |
| name_score       | match.py   | Name similarity to the best candidate, 0 to 1 (name tier only)              | 0.97                |
| best_candidate   | match.py   | Most similar plant name of the same technology                              | Frostham Solar Park |
| net_loss_eur     | analyse.py | `amount_eur` minus the deductible, limited to between 0 and the sum insured | 1000000.00          |
| covered          | analyse.py | True if the loss date falls inside the plant's policy period                | True                |

`net_loss_eur` and `covered` are calculated when the analysis runs; they are not stored in the database.

## Other files

- `claims_answer_key.csv`: the true plant for each claim (`claim_id`, `true_plant_id`). It is created by the generator and used only to measure how accurate the matching is. The matching itself never reads it.

## Assumptions

- USD amounts use a fixed rate of 1 EUR = 1.10 USD.
- All figures per technology (sizes, values, premium rates, claim frequency, loss sizes) are invented and are not market figures.
