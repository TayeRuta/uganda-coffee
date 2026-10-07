# Uganda Coffee: Exports, World Prices and What Reaches Farmers

Six decades of Uganda's coffee exports, and how world coffee prices pass through to the prices farmers are paid. Built from the Coffee Department's own statistics and its monthly reports, with IMF world prices.

**Read the reports:**
- [How much of the coffee boom reached Uganda's farmers?](https://tayeruta.github.io/uganda-coffee/reports/coffee_report.html): exports, prices, farm-gate pass-through and climate
- [Uganda's coffee against the world](https://tayeruta.github.io/uganda-coffee/reports/benchmark_report.html): a benchmark against 21 producers in East Africa, the rest of Africa and the world

## Key findings

- **Exports have more than doubled since 2015/16**, to a record 8.4 million 60-kg bags in 2025/26 (preliminary), worth about US$2.2 billion a year in both 2024/25 and 2025/26.
- **Uganda's robusta sells at 82–100% of the world robusta price; its arabica at about 65–85% of the washed-arabica benchmark**, partly because much of it is sold unwashed (drugar).
- **Farmers' share of the world robusta price rose from about 45% after market liberalisation (1992–93) to 70–80% today.**
- **Prices pass through fast.** About two-thirds of a world price change reaches robusta farmers within the month, and the remaining gap halves in two to three months. Arabica follows more slowly.
- **The 2024–25 farm-gate boom was the world price.** About 96% of the 3.4× rise in robusta farm-gate prices from 2020 to 2025 came from world prices. Prices peaked in February 2025 and are down about a quarter since.
- **The robusta belt is warming fast, and heat costs exports.** Daytime highs in the robusta zones are rising 0.43–0.67 °C per decade (reanalysis; needs a station check). Heat in January–June cuts robusta exports by about 9–16% per standard deviation, and a wet July–December lifts the next crop by about 7–12%. Arabica shows no consistent signal. *Medium confidence.*
- **Coffee income arrives June–September (robusta) and February–May (arabica).** Coffee prices are calmer than maize month to month, but their worst 12-month falls are deeper (−52% to −64% in real terms).

**Benchmark against 21 producers (2021–2025 averages, USDA and FAOSTAT)**

- **Uganda is the world's 6th-largest producer and exporter, and Africa's largest exporter**, with about 4.6% of world exports.
- **It is the fastest-growing of the ten largest producers** (5.0% a year since 2006–10), while most West and Central African robusta producers have shrunk.
- **Its biggest gap is yield**: about 560 kg/ha against Vietnam's 2,900. Uganda's harvested area is imputed by FAOSTAT, so the size of the gap is uncertain. *Low confidence.*
- **It is paid about 85% of the world reference price for its robusta/arabica mix**: above Vietnam (82%) and African robusta peers (68–76%), below India (96%) and Indonesia (106%). *Medium confidence.*
- **It drinks about 4% of its own coffee**, against 35–45% in Ethiopia, Brazil and Indonesia.
- **Its export figures differ by source.** USDA matched the Coffee Department until 2021; for 2024/25 and 2025/26 it is 22–25% lower.

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
│   ├── 01_exports_prices_and_farmgate.ipynb
│   ├── 02_climate_and_exports.ipynb
│   └── 03_global_benchmark.ipynb
├── reports/
│   ├── coffee_report.html           # exports, prices and climate, published on GitHub Pages
│   └── benchmark_report.html        # global benchmark, published on GitHub Pages
├── scripts/
│   ├── gee/uganda_coffee_zones_climate_gee.js   # Earth Engine export: coffee-zone temperature and rainfall
│   ├── fetch_data.py                # downloads every input
│   ├── extract_monthly_reports.py   # reads exports and farm-gate prices from the report PDFs
│   ├── coffee.py                    # shared loading code
│   ├── build_notebooks.py           # generates the notebooks from source
│   └── build_report_data.py         # injects the notebooks' results into the reports
└── requirements.txt
```

## Data and methods

- **Monthly reports.** Exports by type and farm-gate prices are read automatically from 80 monthly reports (January 2020 – August 2026). Each report states its figures twice, in a summary and in tables; the extraction checks one against the other. Fourteen reports contain typing slips (a figure copied from the previous month, a thousands separator written as a full stop, a swapped digit). Each correction is listed in `data/processed/monthly_reports_extracted.csv`.
- **Farm-gate prices.** July 1992 – September 2015 from the Coffee Department's price table; January 2020 onwards from the monthly reports. Prices for late 2015–2019 are not published.
- **Pass-through.** An error-correction model of monthly changes in farm-gate prices (UGX) on changes in the world price converted to UGX, with three lags, testing rises and falls separately. Standard errors are robust to autocorrelation.
- **Exchange rate.** From the Coffee Department table to 2015, then the rate implied by WFP's price conversions.
- **Benchmark.** Peers by rule: every country with at least 1% of world production, plus every African producer above 100,000 bags (USDA, 2021–2025). Countries are grouped as robusta-led (≥70% robusta), arabica-led (≤30%) or mixed, and compared within groups. Price realisation is the FAOSTAT export unit value divided by the IMF reference price for each country's robusta/arabica mix, 2020–2024. Yields are flagged by the share of official area figures behind them.

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
| [ERA5-Land monthly](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR) and [CHIRPS](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY) (coffee-zone temperature and rainfall) | ECMWF/Copernicus; UC Santa Barbara CHC, via Google Earth Engine |
| [Coffee production, supply and distribution](https://apps.fas.usda.gov/psdonline/app/index.html#/app/downloads) | USDA Foreign Agricultural Service |
| [Crop production and trade](https://www.fao.org/faostat/en/#data) (green coffee, all countries) | FAOSTAT |
| [Market prices](https://data.humdata.org/dataset/wfp-food-prices-for-uganda) | World Food Programme, via HDX |

## Limitations

- **Preliminary monthly figures.** Monthly report figures are preliminary and differ from final figures by up to about 2%.
- **Price gap.** Farm-gate prices for late 2015–2019 aren't published, so trends across that gap rely on the two periods either side.
- **Nominal values.** Export values are in nominal US dollars, which overstates real long-run growth.
- **Price basis.** Farm-gate prices are national averages reported by the Coffee Department; prices vary by region and buyer.
- **Benchmark data.** FAOSTAT area and yield are estimated or imputed for many African producers, Uganda included. Export unit values average across grades and buyers. USDA figures are estimates built from production.

## License

Code and analysis: [MIT](LICENSE). The source data keep their providers' terms.
