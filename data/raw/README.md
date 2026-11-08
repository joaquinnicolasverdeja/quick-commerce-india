# Raw data

This folder holds the original survey file, which is **not included in the repository** because it contains respondents' names.

## How to get it

1. Download the dataset from Kaggle: [Quick Commerce Consumer Behavior](https://www.kaggle.com/datasets/vedanshsharma0024/quick-commerce-consumer-behavior).
2. Place the Excel file in this folder with this exact name:

```
Quick Commerce Consumer Behavior (100Responses).xlsx
```

Rename it if the downloaded file has a different name.

The R pipeline (`r/01_clean_segment.R`) reads this file, removes names and produces the anonymised dataset in `data/clean/`.
