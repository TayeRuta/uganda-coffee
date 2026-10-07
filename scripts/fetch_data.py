"""
Download every input dataset for the coffee project.

Usage (from anywhere):
    python scripts/fetch_data.py [--food-prices-repo PATH]
    python scripts/extract_monthly_reports.py

Outputs
  data/raw/statistics/            Coffee Department (MAAIF, formerly UCDA) statistics spreadsheets:
                                  annual exports since FY1964/65, exports by type, monthly farm-gate
                                  prices 1992–2015, FY2022/23 export tables
  data/raw/monthly_reports/       Coffee Department monthly report PDFs, January 2020 onwards (not committed)
  data/raw/world_coffee_prices.csv  IMF monthly prices, robusta and other mild arabica (US cents/lb), via FRED
  data/external/                  consumer price index and WFP market prices, from the uganda-food-prices project
  data/raw/global/psd_coffee.csv            USDA coffee supply and distribution, all countries, 1960 onwards
  data/raw/global/faostat_coffee_production.csv  FAOSTAT green coffee area, yield and production, all countries
  data/raw/global/faostat_coffee_trade.csv       FAOSTAT green coffee export quantity and value, all countries

The CPI and WFP files come from github.com/TayeRuta/uganda-food-prices. If a local copy is given with
--food-prices-repo they are copied from it, otherwise downloaded from GitHub.
"""
import argparse
import io
import re
import shutil
import zipfile
import urllib.parse
import urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, EXT = ROOT / 'data' / 'raw', ROOT / 'data' / 'external'
SITE = 'https://ugandacoffee.go.ug'
STATISTICS = [
    '2023-12/Uganda%27s%20Coffee%20Export%20Tables%20for%20%20FY2022-23.xls',
    '2022-03/Coffee%20Exports%20by%20Destination_%202007-2008%20to%202016-2017.xls',
    '2022-03/Price_Trend_1992_93_2015_USD.xls',
    '2023-06/Average%20Unit%20Prices%20by%20Grades%20for%20FY%202015-2016%20to%20FY%202020-2021.xls',
    '2023-06/Coffee%20Exports%20by%20Grades%2C%20Quantity%20%26%20Unit%20Prices_FY%202015-2016%20to%20FY%202021-2022.xls',
    '2023-06/Coffee%20Exports%20by%20Type%20FY%201991-1992%20to%20FY%202020-2021.xls',
    '2023-06/Coffee%20Exports%20from%20FY%201964-1965%20to%20FY%202021-2022.xls',
]
FRED = {'robusta_usc_lb': 'PCOFFROBUSDM', 'arabica_usc_lb': 'PCOFFOTMUSDM'}
PSD = 'https://apps.fas.usda.gov/psdonline/downloads/psd_coffee_csv.zip'
FAO_PROD = 'https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip'
FAO_TRADE = 'https://bulks-faostat.fao.org/production/Trade_CropsLivestock_E_All_Data.zip'
FOOD_REPO = 'https://raw.githubusercontent.com/TayeRuta/uganda-food-prices/main/'
FOOD_FILES = ['data/raw/fao_cpi_uganda.csv', 'data/raw/wfp_food_prices_uga.csv']


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def report_links():
    links = set()
    for page in range(0, 10):
        html = get(f'{SITE}/index.php/resource-center/reports/monthly-reports?page={page}').decode('utf-8', 'ignore')
        found = re.findall(r'href="(/sites/default/files/[^"]+\.pdf)"', html)
        if not found:
            break
        links.update(found)
    return sorted(links)


def fetch_global():
    """Global coffee data for the benchmark. Only green-coffee rows are kept from the large FAOSTAT files."""
    out = RAW / 'global'
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(get(PSD))) as z:
        name = [n for n in z.namelist() if n.endswith('.csv')][0]
        (out / 'psd_coffee.csv').write_bytes(z.read(name))
    print('USDA coffee database saved')

    with zipfile.ZipFile(io.BytesIO(get(FAO_PROD))) as z:
        name = [n for n in z.namelist() if n.endswith('.csv') and 'All_Data' in n][0]
        chunks = pd.read_csv(z.open(name), encoding='utf-8', chunksize=500_000, low_memory=False)
        prod = pd.concat(c[c['Item'] == 'Coffee, green'] for c in chunks)
    prod.to_csv(out / 'faostat_coffee_production.csv', index=False)
    print(f'FAOSTAT coffee production: {len(prod):,} rows')

    with zipfile.ZipFile(io.BytesIO(get(FAO_TRADE))) as z:
        name = [n for n in z.namelist() if n.endswith('All_Data.csv')][0]
        chunks = pd.read_csv(z.open(name), encoding='utf-8', chunksize=200_000, low_memory=False)
        trade = pd.concat(c[c['Item'] == 'Coffee, green'] for c in chunks)
    trade.to_csv(out / 'faostat_coffee_trade.csv', index=False)
    print(f'FAOSTAT coffee trade: {len(trade):,} rows')


def main(food_repo):
    stats, reports = RAW / 'statistics', RAW / 'monthly_reports'
    for d in (stats, reports, EXT):
        d.mkdir(parents=True, exist_ok=True)

    for path in STATISTICS:
        (stats / urllib.parse.unquote(Path(path).name)).write_bytes(get(f'{SITE}/sites/default/files/{path}'))
    print(f'{len(STATISTICS)} statistics spreadsheets saved')

    links = [l for l in report_links() if 'Directory' not in l]
    new = 0
    for l in links:
        dest = reports / urllib.parse.unquote(Path(l).name)
        if not dest.exists():
            dest.write_bytes(get(SITE + l))
            new += 1
    print(f'{len(links)} monthly reports listed, {new} downloaded')

    prices = None
    for col, sid in FRED.items():
        s = pd.read_csv(io.BytesIO(get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}')))
        s = s.rename(columns={'observation_date': 'date', sid: col})
        prices = s if prices is None else prices.merge(s, on='date')
    prices.to_csv(RAW / 'world_coffee_prices.csv', index=False)
    print(f'World prices: {prices["date"].min()} to {prices["date"].max()}')

    for f in FOOD_FILES:
        dest = EXT / Path(f).name
        if food_repo:
            shutil.copy(Path(food_repo) / f, dest)
        else:
            dest.write_bytes(get(FOOD_REPO + f))
    print('CPI and WFP prices saved')

    fetch_global()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--food-prices-repo', help='local copy of uganda-food-prices (optional)')
    main(ap.parse_args().food_prices_repo)
