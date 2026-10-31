"""Generate synthetic exposure and claims data for power generation plants.

All data is fictional. A fixed random seed makes every run produce the same files.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_PLANTS = 120
USD_PER_EUR = 1.10  # fixed exchange rate, an assumption for synthetic data
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Rough, invented assumptions per technology (synthetic data, not market figures):
# name suffix, capacity range in MW, sum insured per MW, yearly premium rate,
# earliest commissioning year, and plausible countries.
TECHNOLOGIES = {
    "Solar PV": {"suffix": "Solar Park", "mw": (5, 150), "eur_per_mw": 700_000,
                 "rate": 0.0020, "first_year": 2010,
                 "countries": ["DE", "ES", "IT", "FR", "NL", "PL"]},
    "Onshore Wind": {"suffix": "Wind Farm", "mw": (10, 200), "eur_per_mw": 1_300_000,
                     "rate": 0.0030, "first_year": 2000,
                     "countries": ["DE", "ES", "FR", "PL", "GB", "NL"]},
    "Offshore Wind": {"suffix": "Offshore Wind Farm", "mw": (200, 900), "eur_per_mw": 3_500_000,
                      "rate": 0.0040, "first_year": 2010,
                      "countries": ["DE", "NL", "GB", "FR"]},
    "Gas": {"suffix": "Power Station", "mw": (100, 900), "eur_per_mw": 800_000,
            "rate": 0.0025, "first_year": 1990,
            "countries": ["DE", "IT", "NL", "ES", "GB", "PL"]},
    "Hydro": {"suffix": "Hydro Plant", "mw": (10, 300), "eur_per_mw": 2_500_000,
              "rate": 0.0015, "first_year": 1970,
              "countries": ["AT", "DE", "IT", "FR", "ES"]},
    "Battery Storage": {"suffix": "Energy Storage", "mw": (5, 200), "eur_per_mw": 500_000,
                        "rate": 0.0045, "first_year": 2016,
                        "countries": ["DE", "GB", "NL", "IT", "ES"]},
}

# Fictional place names used to build plant names.
PLACES = [
    "Velmora", "Ostrand", "Kaldor", "Brenvik", "Tarsel", "Sonnfeld", "Arnmoor", "Liesach",
    "Dornau", "Falkweil", "Grevlund", "Hollbrook", "Ivenstad", "Jorvale", "Kestrel Bay",
    "Lindmark", "Morwen", "Nordhal", "Orrin", "Pellham", "Quarnby", "Rendal", "Silberau",
    "Thornvik", "Ulmsted", "Varnholt", "Westerlin", "Yarrow Point", "Zellbach", "Ashmere",
    "Belcourt", "Caldspring", "Eiderfeld", "Frostham", "Gallowmere", "Hesperau", "Kirnvale",
    "Merrowdal", "Rookhaven", "Stellwick",
]

# Claims assumptions per technology (invented):
# freq = expected claims per plant per policy year,
# median_loss = typical loss as a share of sum insured,
# causes = possible causes with their probabilities.
CLAIM_PROFILE = {
    "Solar PV": {"freq": 1.0, "median_loss": 0.0008,
                 "causes": {"Hail": 0.35, "Storm": 0.25, "Fire": 0.15,
                            "Flood": 0.10, "Machinery breakdown": 0.15}},
    "Onshore Wind": {"freq": 1.2, "median_loss": 0.0008,
                     "causes": {"Machinery breakdown": 0.45, "Storm": 0.35, "Fire": 0.20}},
    "Offshore Wind": {"freq": 1.4, "median_loss": 0.0010,
                      "causes": {"Machinery breakdown": 0.55, "Storm": 0.35, "Fire": 0.10}},
    "Gas": {"freq": 1.0, "median_loss": 0.0009,
            "causes": {"Machinery breakdown": 0.65, "Fire": 0.30, "Flood": 0.05}},
    "Hydro": {"freq": 0.6, "median_loss": 0.0006,
              "causes": {"Flood": 0.45, "Machinery breakdown": 0.45, "Fire": 0.10}},
    "Battery Storage": {"freq": 1.6, "median_loss": 0.0015,
                        "causes": {"Battery thermal event": 0.35, "Machinery breakdown": 0.40,
                                   "Fire": 0.15, "Flood": 0.10}},
}

# How the same technology may be written by different people
TECH_SPELLINGS = {
    "Solar PV": ["PV", "Solar", "solar pv"],
    "Onshore Wind": ["Wind Onshore", "onshore wind"],
    "Offshore Wind": ["Wind Offshore", "offshore"],
    "Gas": ["Gas Turbine", "CCGT"],
    "Hydro": ["Hydropower", "hydro"],
    "Battery Storage": ["BESS", "Battery"],
}

# Plants that appear in claims but not in the exposure list
UNKNOWN_PLANTS = [
    ("PG-0131", "Norrbeck Solar Park", "Solar PV"),
    ("PG-0137", "Halvsund Wind Farm", "Onshore Wind"),
    ("PG-0142", "Corvane Energy Storage", "Battery Storage"),
    ("PG-0150", "Tessgard Power Station", "Gas"),
]


def make_exposure(rng):
    """Create one row per insured plant (clean), then add the kW/MW problem."""
    rows = []
    used_names = set()

    for i in range(1, N_PLANTS + 1):
        tech = str(rng.choice(list(TECHNOLOGIES)))
        spec = TECHNOLOGIES[tech]

        # Unique fictional name, e.g. "Velmora Solar Park"
        name = f"{rng.choice(PLACES)} {spec['suffix']}"
        while name in used_names:
            name = f"{rng.choice(PLACES)} {spec['suffix']}"
        used_names.add(name)

        capacity_mw = round(float(rng.uniform(*spec["mw"])), 1)
        sum_insured = int(
            round(capacity_mw * spec["eur_per_mw"], -5))  # nearest 100k
        # nearest 1k
        premium = int(round(sum_insured * spec["rate"], -3))
        deductible = max(100_000, int(round(sum_insured * 0.005, -4)))

        # Policy runs 1 or 2 years, starting on the 1st of a month in 2022 or 2023
        start = pd.Timestamp(year=int(rng.integers(2022, 2024)),
                             month=int(rng.integers(1, 13)), day=1)
        end = start + \
            pd.DateOffset(years=int(rng.integers(1, 3))) - pd.Timedelta(days=1)

        rows.append({
            "plant_id": f"PG-{i:04d}",
            "plant_name": name,
            "country": str(rng.choice(spec["countries"])),
            "technology": tech,
            "capacity": capacity_mw,
            "capacity_unit": "MW",
            "commissioning_year": int(rng.integers(spec["first_year"], 2022)),
            "sum_insured_eur": sum_insured,
            "deductible_eur": deductible,
            "annual_premium_eur": premium,
            "policy_start": start.strftime("%Y-%m-%d"),
            "policy_end": end.strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(rows)

    # Messy on purpose: about 10 % of capacities given in kW instead of MW
    in_kw = rng.random(len(df)) < 0.10
    df.loc[in_kw, "capacity"] = (df.loc[in_kw, "capacity"] * 1000).round(0)
    df.loc[in_kw, "capacity_unit"] = "kW"
    return df


def make_clean_claims(rng, exposure):
    """Create realistic claims for the insured plants, all clean and correct."""
    rows = []
    for plant in exposure.itertuples():
        profile = CLAIM_PROFILE[plant.technology]
        start = pd.Timestamp(plant.policy_start)
        end = pd.Timestamp(plant.policy_end)
        years = ((end - start).days + 1) / 365.25

        # How many claims this plant has: random, around freq x years
        n_claims = int(rng.poisson(profile["freq"] * years))

        for _ in range(n_claims):
            loss_date = start + \
                pd.Timedelta(days=int(rng.integers(0, (end - start).days + 1)))
            cause = str(rng.choice(
                list(profile["causes"]), p=list(profile["causes"].values())))

            # Most losses are small; about 2 % are large losses
            if rng.random() < 0.02:
                share = rng.uniform(0.02, 0.10)
            else:
                share = min(0.5, rng.lognormal(
                    np.log(profile["median_loss"]), 1.2))
            amount_eur = round(plant.deductible_eur +
                               share * plant.sum_insured_eur, 2)

            rows.append({
                "plant_id": plant.plant_id,
                "plant_name": plant.plant_name,
                "technology": plant.technology,
                "loss_date": loss_date,
                "cause": cause,
                "amount_eur": amount_eur,
            })

    # A few claims for plants that are not in the exposure list
    for plant_id, name, tech in UNKNOWN_PLANTS:
        rows.append({
            "plant_id": plant_id,
            "plant_name": name,
            "technology": tech,
            "loss_date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 700))),
            "cause": str(rng.choice(list(CLAIM_PROFILE[tech]["causes"]))),
            "amount_eur": round(float(rng.uniform(150_000, 2_000_000)), 2),
        })

    claims = pd.DataFrame(rows).sort_values("loss_date").reset_index(drop=True)
    claims.insert(0, "claim_id", [
                  f"CL-{i:05d}" for i in range(1, len(claims) + 1)])
    return claims


def add_typo(name, rng):
    """Change a plant name slightly: drop a letter, swap two letters, or change case."""
    kind = rng.integers(0, 3)
    i = int(rng.integers(1, len(name) - 2))
    if kind == 0:
        return name[:i] + name[i + 1:]
    if kind == 1:
        return name[:i] + name[i + 1] + name[i] + name[i + 2:]
    return name.upper() if rng.random() < 0.5 else name.lower()


def messy_id(plant_id, rng):
    """Write a plant ID in another format: 'pg12' or 'PG 12'."""
    number = int(plant_id.split("-")[1])
    return f"pg{number}" if rng.random() < 0.5 else f"PG {number}"


def format_amount(amount):
    """Write an amount as text, in German, English or plain format."""
    english = f"{amount:,.2f}"                                     # 1,250,000.00
    german = english.replace(",", "X").replace(
        ".", ",").replace("X", ".")  # 1.250.000,00
    return english, german, f"{amount:.0f}"


def make_messy(claims, exposure, rng):
    """Turn clean claims into raw claims with the problems listed in the data dictionary."""
    df = claims.copy()
    n = len(df)
    policy = exposure.set_index("plant_id")[["policy_start", "policy_end"]]

    # Some loss dates fall outside the policy period
    for i in df.index[rng.random(n) < 0.05]:
        pid = df.at[i, "plant_id"]
        if pid in policy.index:
            shift = pd.Timedelta(days=int(rng.integers(10, 200)))
            if rng.random() < 0.5:
                df.at[i, "loss_date"] = pd.Timestamp(
                    policy.at[pid, "policy_start"]) - shift
            else:
                df.at[i, "loss_date"] = pd.Timestamp(
                    policy.at[pid, "policy_end"]) + shift

    # Some amounts in USD instead of EUR
    in_usd = rng.random(n) < 0.10
    df["currency"] = np.where(in_usd, "USD", "EUR")
    df.loc[in_usd, "amount_eur"] = (
        df.loc[in_usd, "amount_eur"] * USD_PER_EUR).round(2)

    # Amounts as text in mixed formats
    amounts = []
    for amount in df["amount_eur"]:
        english, german, plain = format_amount(amount)
        amounts.append(
            str(rng.choice([english, german, plain], p=[0.4, 0.4, 0.2])))
    df["claim_amount"] = amounts

    # Dates in mixed formats
    dates = []
    for d in df["loss_date"]:
        formats = [d.strftime("%Y-%m-%d"),
                   d.strftime("%d.%m.%Y"), d.strftime("%d %b %Y")]
        dates.append(str(rng.choice(formats, p=[0.5, 0.3, 0.2])))
    df["loss_date"] = dates

    # Technology written in different ways
    techs = []
    for tech in df["technology"]:
        techs.append(tech if rng.random() < 0.5 else str(
            rng.choice(TECH_SPELLINGS[tech])))
    df["technology"] = techs

    # Typos in plant names
    df["plant_name"] = [add_typo(name, rng) if rng.random() < 0.15 else name
                        for name in df["plant_name"]]

    # Plant IDs: some in another format, some missing
    ids = []
    for pid in df["plant_id"]:
        r = rng.random()
        if r < 0.08:
            ids.append("")
        elif r < 0.23:
            ids.append(messy_id(pid, rng))
        else:
            ids.append(pid)
    df["plant_id"] = ids

    # Some claims entered twice, then shuffle the row order
    duplicates = df.sample(frac=0.04, random_state=SEED)
    df = pd.concat([df, duplicates]).sample(
        frac=1, random_state=SEED).reset_index(drop=True)

    columns = ["claim_id", "plant_id", "plant_name", "technology",
               "loss_date", "cause", "claim_amount", "currency"]
    return df[columns]


def main():
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    exposure = make_exposure(rng)
    clean_claims = make_clean_claims(rng, exposure)
    claims = make_messy(clean_claims, exposure, rng)

    exposure.to_csv(OUT_DIR / "exposure.csv", index=False)
    claims.to_csv(OUT_DIR / "claims.csv", index=False)

    # Answer key: the true plant for each claim. Used only to check the matcher later.
    clean_claims[["claim_id", "plant_id"]].rename(columns={"plant_id": "true_plant_id"}) \
        .to_csv(OUT_DIR / "claims_answer_key.csv", index=False)

    print(f"exposure.csv: {len(exposure)} plants")
    print(
        f"claims.csv: {len(claims)} rows ({len(clean_claims)} real claims + duplicates)")
    print(claims.head(10).to_string())


if __name__ == "__main__":
    main()
