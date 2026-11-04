"""Analyse the matched claims: loss ratio, frequency and severity by technology."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "powergen.db"
OUT_DIR = ROOT / "output"


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
    cols = ["plant_id", "plant_name", "technology", "sum_insured_eur",
            "deductible_eur", "policy_start", "policy_end"]
    df = claims.merge(exposure[cols], left_on="matched_plant_id", right_on="plant_id",
                      how="inner", suffixes=("_claim", ""))

    # Net loss can't be negative, and the insurer never pays more than the sum insured
    df["net_loss_eur"] = (df["amount_eur"] - df["deductible_eur"]).clip(
        lower=0, upper=df["sum_insured_eur"])
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
                                               net_loss_eur=(
                                                   "net_loss_eur", "sum"),
                                               largest_eur=("net_loss_eur", "max"))
    df = side_a.join(side_b).fillna(0)
    df["frequency"] = df["claims"] / df["plant_years"]
    df["severity_eur"] = df["net_loss_eur"] / df["claims"]
    df["loss_ratio"] = df["net_loss_eur"] / df["premium_eur"]
    return df.sort_values("loss_ratio", ascending=False)


def largest_losses(claims, n=10):
    """The n largest covered losses, with their size compared to the plant's value."""
    top = claims[claims["covered"]].nlargest(n, "net_loss_eur").copy()
    top["share_of_value_pct"] = top["net_loss_eur"] / \
        top["sum_insured_eur"] * 100
    return top[["claim_id", "plant_name", "technology", "cause",
                "net_loss_eur", "share_of_value_pct"]]


def lr_without_top(claims, summary, n):
    """Loss ratio per technology after removing its n largest covered losses."""
    covered = claims[claims["covered"]]
    top_n = covered.groupby("technology")["net_loss_eur"].apply(
        lambda losses: losses.nlargest(n).sum())
    return (summary["net_loss_eur"] - top_n) / summary["premium_eur"]


def save_results(matched, claims, summary):
    """Save the final answers as readable CSV files in output/."""
    covered = claims[claims["covered"]]
    outside = claims[~claims["covered"]]
    unmatched = matched[matched["match_method"] == "unmatched"]
    premium = summary["premium_eur"].sum()
    net_loss = covered["net_loss_eur"].sum()

    portfolio = pd.DataFrame([
        ("Plants insured", str(summary["plants"].sum())),
        ("Claims (after removing duplicates)", str(len(matched))),
        ("Claims matched to a plant", str(len(matched) - len(unmatched))),
        ("Claims with no matching plant", str(len(unmatched))),
        ("Claims outside the policy period", str(len(outside))),
        ("Covered claims", str(len(covered))),
        ("Premium (EUR m)", f"{premium / 1e6:,.1f}"),
        ("Gross losses (EUR m)", f"{covered['amount_eur'].sum() / 1e6:,.1f}"),
        ("Net losses after deductible (EUR m)", f"{net_loss / 1e6:,.1f}"),
        ("Loss ratio", f"{net_loss / premium:.2f}"),
    ], columns=["Measure", "Value"])

    by_tech = pd.DataFrame({
        "Technology": summary.index,
        "Plants": summary["plants"],
        "Plant-years": summary["plant_years"].round(1),
        "Premium (EUR m)": (summary["premium_eur"] / 1e6).round(2),
        "Covered claims": summary["claims"].astype(int),
        "Net losses (EUR m)": (summary["net_loss_eur"] / 1e6).round(2),
        "Frequency (claims per plant-year)": summary["frequency"].round(2),
        "Severity (EUR k per claim)": (summary["severity_eur"] / 1e3).round(0).astype(int),
        "Loss ratio": summary["loss_ratio"].round(2),
        "Loss ratio without largest claim": summary["lr_without_top1"].round(2),
        "Loss ratio without 2 largest claims": summary["lr_without_top2"].round(2),
    })

    top = largest_losses(claims)
    largest = pd.DataFrame({
        "Claim": top["claim_id"],
        "Plant": top["plant_name"],
        "Technology": top["technology"],
        "Cause": top["cause"],
        "Net loss (EUR m)": (top["net_loss_eur"] / 1e6).round(2),
        "Share of plant value (%)": top["share_of_value_pct"].round(2),
    })

    review = pd.concat([
        pd.DataFrame({
            "Claim": unmatched["claim_id"],
            "Plant": unmatched["plant_name"],
            "Reason": "No matching plant in the portfolio",
            "Detail": "Closest plant: " + unmatched["best_candidate"].fillna("none"),
            "Amount (EUR k)": (unmatched["amount_eur"] / 1e3).round(0).astype(int),
        }),
        pd.DataFrame({
            "Claim": outside["claim_id"],
            "Plant": outside["plant_name"],
            "Reason": "Loss date outside the policy period",
            "Detail": "Loss " + outside["loss_date_clean"].dt.strftime("%Y-%m-%d")
                      + ", policy " +
            outside["policy_start"].dt.strftime("%Y-%m-%d")
            + " to " + outside["policy_end"].dt.strftime("%Y-%m-%d"),
            "Amount (EUR k)": (outside["amount_eur"] / 1e3).round(0).astype(int),
        }),
    ])

    OUT_DIR.mkdir(exist_ok=True)
    portfolio.to_csv(OUT_DIR / "1_portfolio.csv", index=False)
    by_tech.to_csv(OUT_DIR / "2_by_technology.csv", index=False)
    largest.to_csv(OUT_DIR / "3_largest_losses.csv", index=False)
    review.to_csv(OUT_DIR / "4_review_queue.csv", index=False)


def main():

    matched, exposure = load()
    claims = add_policy_info(matched, exposure)
    covered = claims[claims["covered"]]

    print("Claims linked to a plant:", len(claims))
    print("Covered:                 ", len(covered))
    print("Outside policy period:   ", len(claims) - len(covered))
    print(f"Gross losses (covered):   {covered['amount_eur'].sum():,.0f}")
    print(f"Net losses (covered):     {covered['net_loss_eur'].sum():,.0f}")

    summary = summary_by_technology(claims, exposure)
    summary["lr_without_top1"] = lr_without_top(claims, summary, n=1)
    summary["lr_without_top2"] = lr_without_top(claims, summary, n=2)

    total_premium = summary["premium_eur"].sum()
    print(f"Total premium:            {total_premium:,.0f}")
    print(
        f"Portfolio loss ratio:     {summary['net_loss_eur'].sum() / total_premium:.2f}")

    pd.options.display.float_format = "{:,.2f}".format
    print()
    print("Results by technology (sorted from worst to best loss ratio)")
    print("frequency = claims per plant-year | severity = average net loss per claim")
    print(summary.to_string())

    print()
    print("Top 10 largest losses in the whole portfolio")
    print("share_of_value_pct = net loss as % of the plant's sum insured")
    print(largest_losses(claims).to_string(index=False))

    for tech in summary.index:
        tech_claims = claims[claims["technology"] == tech]
        print()
        print(
            f"Largest losses: {tech} (loss ratio {summary.loc[tech, 'loss_ratio']:.2f})")
        print(largest_losses(tech_claims, n=3).to_string(index=False))

    save_results(matched, claims, summary)                          # NEW
    print(f"\nResults saved to {OUT_DIR.relative_to(ROOT)}/")      # NEW


if __name__ == "__main__":
    main()
