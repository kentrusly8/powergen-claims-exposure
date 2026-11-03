"""Streamlit app: portfolio overview, plant lookup and review queue."""

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
    st.bar_chart(summary["loss_ratio"])
    st.dataframe(summary)

    st.subheader("Largest losses")
    st.dataframe(largest_losses(claims), hide_index=True)
