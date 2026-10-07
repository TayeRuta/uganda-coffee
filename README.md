# Uganda Coffee: Exports, World Prices and What Reaches Farmers

Six decades of Uganda's coffee exports, and how world coffee prices pass through to the prices farmers are paid. Built from the Coffee Department's own statistics and its monthly reports, with IMF world prices.

**Read the report: [How much of the coffee boom reached Uganda's farmers?](https://tayeruta.github.io/uganda-coffee/reports/coffee_report.html)**

## Key findings

- **Exports have more than doubled since 2015/16**, to a record 8.4 million 60-kg bags in 2025/26 (preliminary), worth about US$2.2 billion a year in both 2024/25 and 2025/26.
- **Uganda's robusta sells at 82–100% of the world robusta price; its arabica at about 65–85% of the washed-arabica benchmark**, partly because much of it is sold unwashed (drugar).
- **Farmers' share of the world robusta price rose from about 45% after market liberalisation (1992–93) to 70–80% today.**
- **Prices pass through fast.** About two-thirds of a world price change reaches robusta farmers within the month, and the remaining gap halves in two to three months. Arabica follows more slowly.
- **The 2024–25 farm-gate boom was the world price.** About 96% of the 3.4× rise in robusta farm-gate prices from 2020 to 2025 came from world prices. Prices peaked in February 2025 and are down about a quarter since.
- **Coffee income arrives June–September (robusta) and February–May (arabica).** Coffee prices are calmer than maize month to month, but their worst 12-month falls are deeper (−52% to −64% in real terms).

## Repository structure

```
.
├── data/
│   ├── raw/
│   │   ├── statistics/              # Coffee Department spreadsheets (exports since FY1964/65, farm-gate prices 1992–2015)
│   │   ├── monthly_reports/         # monthly report PDFs, 2020 onwards (not committed; see fetch_data.py)
│   │   └── world_coffee_prices.csv  # IMF robusta and arabica prices, via FRED
│   ├── external/                    # consumer prices and WFP prices, from the uganda-food-prices project
│   └── processed/                   # figures extracted from the reports, and result tables
├── notebooks/
│   └── 01_exports_prices_and_farmgate.ipynb
├── reports/
│   └── coffee_report.html           # the write-up, published on GitHub Pages
├── scripts/
│   ├── fetch_data.py                # downloads every input
│   ├── extract_monthly_reports.py   # reads exports and farm-gate prices from the report PDFs
│   ├── coffee.py                    # shared loading code
│   ├── build_notebooks.py           # generates the notebooks from source
│   └── build_report_data.py         # injects the notebook's results into the report
└── requirements.txt
```

## Data and methods

- **Monthly reports.** Exports by type and farm-gate prices are read automatically from 80 monthly reports (January 2020 – August 2026). Each report states its figures twice, in a summary and in tables; the extraction checks one against the other. Fourteen reports contain typing slips (a figure copied from the previous month, a thousands separator written as a full stop, a swapped digit). Each correction is listed in `data/processed/monthly_reports_extracted.csv`.
- **Farm-gate prices.** July 1992 – September 2015 from the Coffee Department's price table; January 2020 onwards from the monthly reports. Prices for late 2015–2019 are not published.
- **Pass-through.** An error-correction model of monthly changes in farm-gate prices (UGX) on changes in the world price converted to UGX, with three lags, testing rises and falls separately. Standard errors are robust to autocorrelation.
- **Exchange rate.** From the Coffee Department table to 2015, then the rate implied by WFP's price conversions.

## Reproducing the analysis

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_data.py                 # or: --food-prices-repo /path/to/uganda-food-prices
python scripts/extract_monthly_reports.py
python scripts/build_notebooks.py
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
python scripts/build_report_data.py          # refresh the numbers in the report
```

## Data sources

| Dataset | Provider |
|---|---|
| [Coffee statistics and monthly reports](https://ugandacoffee.go.ug/index.php/resource-center/statistics) | Coffee Department, Ministry of Agriculture, Animal Industry and Fisheries (formerly Uganda Coffee Development Authority) |
| [Global prices of robusta and other mild arabica](https://fred.stlouisfed.org/series/PCOFFROBUSDM) | IMF, via FRED |
| [Consumer price index](https://www.fao.org/faostat/en/#data/CP) | FAOSTAT |
| [Market prices](https://data.humdata.org/dataset/wfp-food-prices-for-uganda) | World Food Programme, via HDX |

## Limitations

- **Preliminary monthly figures.** Monthly report figures are preliminary and differ from final figures by up to about 2%.
- **Price gap.** Farm-gate prices for late 2015–2019 aren't published, so trends across that gap rely on the two periods either side.
- **Nominal values.** Export values are in nominal US dollars, which overstates real long-run growth.
- **Price basis.** Farm-gate prices are national averages reported by the Coffee Department; prices vary by region and buyer.

## License

Code and analysis: [MIT](LICENSE). The source data keep their providers' terms.
