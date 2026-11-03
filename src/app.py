"""Streamlit app: portfolio overview, plant lookup and review queue."""

import altair as alt
import pandas as pd
import streamlit as st

from analyse import (add_policy_info, largest_losses, load,
                     lr_without_top, summary_by_technology)

st.set_page_config(page_title="PowerGen Claims–Exposure", layout="wide")


@st.cache_data
def get_data():
    """Load everything once; Streamlit keeps the result in memory between clicks."""
    matched, exposure = load()
    claims = add_policy_info(matched, exposure)
    summary = summary_by_technology(claims, exposure)
    summary["lr_without_top2"] = lr_without_top(claims, summary, n=2)
    return matched, claims, exposure, summary


matched, claims, exposure, summary = get_data()
money = "€{:,.0f}"

st.title("PowerGen Claims–Exposure")
st.caption("Synthetic data only. No real plants, clients or insurers.")

overview, lookup, review = st.tabs(
    ["Portfolio overview", "Plant lookup", "Review queue"])

with overview:
    total_premium = summary["premium_eur"].sum()
    total_loss = summary["net_loss_eur"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Premium", f"€{total_premium / 1e6:,.1f}m")
    col2.metric("Net losses", f"€{total_loss / 1e6:,.1f}m")
    col3.metric("Loss ratio", f"{total_loss / total_premium:.2f}")

    st.subheader("Loss ratio by technology")
    chart_data = summary.reset_index()
    bars = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("loss_ratio:Q", title="Loss ratio"),
        y=alt.Y("technology:N", sort="-x", title=None),
        color=alt.condition(alt.datum.loss_ratio > 1,
                            alt.value("#e45756"), alt.value("#4c78a8")),
    )
    break_even = alt.Chart(pd.DataFrame({"x": [1]})).mark_rule(
        strokeDash=[4, 4]).encode(x="x:Q")
    st.altair_chart(bars + break_even, use_container_width=True)

    st.dataframe(summary.style.format({
        "plant_years": "{:.1f}", "premium_eur": money, "net_loss_eur": money,
        "largest_eur": money, "severity_eur": money, "frequency": "{:.2f}",
        "loss_ratio": "{:.2f}", "lr_without_top2": "{:.2f}",
    }))
    st.subheader("Largest losses")
    st.dataframe(largest_losses(claims).style.format({
        "net_loss_eur": money, "share_of_value_pct": "{:.2f} %",
    }), hide_index=True)

with lookup:
    choice = st.selectbox(
        "Choose a plant", exposure["plant_name"].sort_values())
    plant = exposure[exposure["plant_name"] == choice].iloc[0]

    plant_claims = claims[claims["plant_id"] == plant["plant_id"]]
    covered_claims = plant_claims[plant_claims["covered"]]
    years = ((plant["policy_end"] - plant["policy_start"]).days + 1) / 365.25
    premium = plant["annual_premium_eur"] * years
    net_loss = covered_claims["net_loss_eur"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Technology", plant["technology"])
    col2.metric("Sum insured", f"€{plant['sum_insured_eur'] / 1e6:,.1f}m")
    col3.metric("Premium (policy period)", f"€{premium:,.0f}")
    col4.metric("Loss ratio", f"{net_loss / premium:.2f}")

    st.caption(f"{plant['plant_id']} · {plant['country']} · {plant['capacity_mw']} MW · "
               f"policy {plant['policy_start']:%d %b %Y} – {plant['policy_end']:%d %b %Y}")

    st.subheader(f"Claims ({len(plant_claims)})")
    if plant_claims.empty:
        st.info("No claims for this plant during its policy period.")
    else:
        table = plant_claims[["claim_id", "loss_date_clean", "cause", "amount_eur",
                              "net_loss_eur", "covered", "match_method"]].sort_values("loss_date_clean")
        table["loss_date_clean"] = table["loss_date_clean"].dt.date
        st.dataframe(table.style.format({"amount_eur": money, "net_loss_eur": money}),
                     hide_index=True)
with review:
    st.write(
        "Claims that need a human decision before they can be used in the analysis.")

    unmatched = matched[matched["match_method"] == "unmatched"]
    st.subheader(f"No matching plant ({len(unmatched)})")
    st.caption("No ID or name in the portfolio matched. The closest candidate is shown "
               "for context; name scores below 0.90 are not accepted.")
    st.dataframe(unmatched[["claim_id", "plant_id", "plant_name", "technology_clean",
                            "amount_eur", "best_candidate", "name_score"]]
                 .style.format({"amount_eur": money, "name_score": "{:.2f}"}),
                 hide_index=True)

    spot_check = matched[(matched["match_method"] == "name")
                         & (matched["name_score"] < 1)]
    st.subheader(f"Name matches to spot-check ({len(spot_check)})")
    st.caption("Matched by name, but the spelling differs from the plant list.")
    st.dataframe(spot_check[["claim_id", "plant_name", "best_candidate", "name_score"]]
                 .style.format({"name_score": "{:.2f}"}),
                 hide_index=True)

    outside = claims[~claims["covered"]].copy()
    st.subheader(f"Outside the policy period ({len(outside)})")
    st.caption(
        "Linked to a plant, but the loss date falls outside its policy, so it is not covered.")
    for col in ["loss_date_clean", "policy_start", "policy_end"]:
        outside[col] = outside[col].dt.date
    st.dataframe(outside[["claim_id", "plant_name", "loss_date_clean",
                          "policy_start", "policy_end", "amount_eur"]]
                 .style.format({"amount_eur": money}),
                 hide_index=True)
