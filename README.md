# Q-Commerce Tracker: Customer Segmentation of India's Instant Delivery Market

**[Live app](LINK_TO_STREAMLIT_APP)** · **[Dataset on Kaggle](https://www.kaggle.com/datasets/vedanshsharma0024/quick-commerce-consumer-behavior)**

![App screenshot](images/app_screenshot.png)

## Overview

Quick-commerce platforms promise grocery delivery in minutes, but not every customer is worth the same to them. This project segments respondents of a consumer survey by how much they spend each month, then compares the segments on who they are, what they order and what they value, to show where a platform should focus.

It is a refactored version of an MSc Business Analytics project (University of Exeter): data cleaning and segmentation were moved into a reproducible R pipeline, and an interactive Streamlit app presents the results.

## Pipeline

| Step | Tool | What it does |
|---|---|---|
| Cleaning | R | Selects the variables used in the analysis, removes respondent names, unifies free-text variants (e.g. city spellings) |
| Segmentation | R | Estimates each respondent's monthly spend (EMV) and splits the sample into quartiles |
| Descriptive statistics | R | EMV summary and profile distributions by segment |
| Visualisation | Python (Streamlit, Plotly) | Interactive dashboard to compare segments side by side |

## Segmentation method

**EMV (Estimated Monthly Value)** = midpoint of the spend-per-order range × orders per month.

Respondents are split into four segments by EMV quartiles: Bronze (Q1), Silver (Q2), Gold (Q3) and Diamond (Q4). Quartiles were chosen because there are no external thresholds for a "high-value" customer in this market, and they are robust to the strong skew in spending.

| Segment | n | Mean EMV (₹) | Median EMV (₹) |
|---|---|---|---|
| Bronze (Q1) | 31 | 256 | 300 |
| Silver (Q2) | 33 | 839 | 750 |
| Gold (Q3) | 26 | 2,327 | 3,000 |
| Diamond (Q4) | 18 | 20,389 | 11,500 |

The Diamond segment shows why the median matters: two respondents with an EMV of ₹105,000 nearly double the segment's mean.

## Key insights

<!-- Add 2–3 findings from the analysis here -->
- [Insight 1]
- [Insight 2]
- [Insight 3]

## The app

The dashboard is organised in three modules, all filterable by segment:

1. **Who is the customer?** Demographic and socioeconomic profile.
2. **Order trends.** Product categories, expected delivery time and time of day.
3. **What does the customer value?** Choice factors, importance of discounts, switching motivations and suggestions.

## Repository structure

```
├── app.py                      Streamlit dashboard
├── requirements.txt            Python dependencies
├── r/
│   ├── 01_clean_segment.R      Cleaning, EMV and segmentation
│   └── 02_descriptive_stats.R  Descriptive statistics by segment
├── data/
│   ├── raw/                    Original survey (not included, see below)
│   └── clean/                  Anonymised, segmented dataset used by the app
└── outputs/                    Descriptive statistics tables
```

## How to reproduce

1. Download the dataset from [Kaggle](https://www.kaggle.com/datasets/vedanshsharma0024/quick-commerce-consumer-behavior) and place the Excel file in `data/raw/` (see `data/raw/README.md`).
2. Open `quick-commerce-india.Rproj` in RStudio, install `readxl`, `dplyr` and `readr`, and run `r/01_clean_segment.R` and then `r/02_descriptive_stats.R`.
3. Install the Python dependencies and launch the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The cleaned dataset is already included, so step 3 works on its own.

## Limitations

- **Sample size and location.** 109 responses, mostly from Amritsar: useful for exploring patterns, not for generalising to the Indian market.
- **Estimated spend.** The survey records spend in ranges, so EMV relies on range midpoints and assumed monthly frequencies.
- **Survey design.** Some answer options overlap (e.g. income "100000+" and "200000+").
- **Data exclusions.** One response with an invalid city entry is excluded from the dashboard after segmentation.

## Author

Joaquin Nicolas · [Portfolio](LINK_TO_PORTFOLIO)
