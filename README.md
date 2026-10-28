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
