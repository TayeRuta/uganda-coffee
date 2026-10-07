"""
Shared loading code for the coffee analysis. Imported by the notebooks and the report builder.

Units: farm-gate prices in UGX per kg; world and export prices in US$ per kg; volumes in 60-kg bags.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, EXT, PROC = ROOT / 'data' / 'raw', ROOT / 'data' / 'external', ROOT / 'data' / 'processed'
STATS = RAW / 'statistics'
LB_PER_KG = 2.20462
BAG_KG = 60


def _period(s):
    return pd.to_datetime(s).dt.to_period('M')


# ---------------------------------------------------------------- world prices
def load_world():
    """IMF monthly world prices (via FRED), converted from US cents/lb to US$/kg."""
    w = pd.read_csv(RAW / 'world_coffee_prices.csv')
    w.index = _period(w['date'])
    return pd.DataFrame({'robusta_usd_kg': w['robusta_usc_lb'] / 100 * LB_PER_KG,
                         'arabica_usd_kg': w['arabica_usc_lb'] / 100 * LB_PER_KG})


# ---------------------------------------------------------------- exchange rate
def load_fx():
    """UGX per US$, monthly. 1992–2015 from the Coffee Department's farm-gate table; from 2006 the
    median rate implied by WFP's own UGX/US$ price conversions. Where both exist, the Coffee
    Department figure is used."""
    fg = _farmgate_history()
    fx_cd = fg['fx']
    wfp = pd.read_csv(EXT / 'wfp_food_prices_uga.csv', skiprows=[1])
    wfp['price'] = pd.to_numeric(wfp['price'], errors='coerce')
    wfp['usdprice'] = pd.to_numeric(wfp['usdprice'], errors='coerce')
    wfp = wfp[wfp['usdprice'] > 0]
    fx_wfp = (wfp['price'] / wfp['usdprice']).groupby(_period(wfp['date'])).median()
    return fx_cd.combine_first(fx_wfp).sort_index().rename('ugx_per_usd')


# ---------------------------------------------------------------- consumer prices
def load_cpi():
    c = pd.read_csv(EXT / 'fao_cpi_uganda.csv')
    c = c[c['item'].str.contains('General')]
    idx = pd.PeriodIndex([pd.Period(year=y, month=m, freq='M') for y, m in zip(c['year'], c['month'])])
    return pd.Series(c['value'].values, index=idx).sort_index().rename('cpi')


# ---------------------------------------------------------------- farm-gate prices
def _farmgate_history():
    f = pd.read_excel(STATS / 'Price_Trend_1992_93_2015_USD.xls', header=None)
    d = f.iloc[5:, 1:6].copy()
    d.columns = ['month', 'kiboko_ugx', 'faq_ugx', 'parchment_ugx', 'fx']
    d = d[pd.to_datetime(d['month'], errors='coerce').notna()]
    d.index = _period(d['month'])
    # April 2004 appears twice with different prices and exchange rates, and both imply farmers were
    # paid more than the world price. The month can't be resolved, so both rows are dropped.
    d = d[~d.index.duplicated(keep=False)]
    return d.drop(columns='month').astype(float)


def load_farmgate():
    """Monthly farm-gate prices (UGX/kg): July 1992 – September 2015 from the Coffee Department's
    price table, January 2020 onwards from its monthly reports. Kiboko is dried robusta cherry,
    FAQ is hulled robusta (green bean), parchment is washed arabica before hulling.
    The 2015–2019 months are not published and stay missing."""
    h = _farmgate_history()[['kiboko_ugx', 'faq_ugx', 'parchment_ugx']]
    h['source'] = 'price table 1992–2015'
    m = pd.read_csv(PROC / 'monthly_reports_extracted.csv')
    m.index = pd.PeriodIndex(m['month'], freq='M')
    m = m[['kiboko_ugx', 'faq_ugx', 'parchment_ugx']].copy()
    m['source'] = 'monthly reports 2020–'
    full = pd.concat([h, m]).sort_index()
    full = full[~full.index.duplicated(keep='last')]
    return full.reindex(pd.period_range(full.index.min(), full.index.max(), freq='M'))


# ---------------------------------------------------------------- exports
def load_exports_monthly():
    """Monthly exports by type from the monthly reports, January 2020 onwards (preliminary figures)."""
    m = pd.read_csv(PROC / 'monthly_reports_extracted.csv')
    m.index = pd.PeriodIndex(m['month'], freq='M')
    out = m[['total_bags', 'total_usd_m', 'robusta_bags', 'robusta_usd_m', 'arabica_bags', 'arabica_usd_m']].copy()
    for t in ['total', 'robusta', 'arabica']:
        out[f'{t}_usd_kg'] = out[f'{t}_usd_m'] * 1e6 / (out[f'{t}_bags'] * BAG_KG)
    return out


def coffee_year(p):
    """Financial year label (July–June) for a monthly period, e.g. 2024-07 -> '2024/25'."""
    y = p.year if p.month >= 7 else p.year - 1
    return f'{y}/{str(y + 1)[-2:]}'


def load_exports_annual():
    """Annual exports by financial year (July–June): FY1964/65–2021/22 from the Coffee Department's
    table (robusta/arabica split from FY1991/92), FY2022/23 from its export tables, and later years
    summed from the monthly reports."""
    t = pd.read_excel(STATS / 'Coffee Exports from FY 1964-1965 to FY 2021-2022.xls', header=None)
    t = t.iloc[5:, [1, 2, 4]].dropna()
    t.columns = ['fy', 'total_bags', 'total_usd']
    # Labels are inconsistent: '98/99 ', '"01/02', '  02/03', '2010/11'. Normalise to '1998/99'.
    t['fy'] = t['fy'].astype(str).str.replace(r'[^0-9/]', '', regex=True)
    t = t[t['fy'].str.match(r'^(\d{2}|\d{4})/\d{2}$')]

    def full_fy(s):
        a, b = s.split('/')
        if len(a) == 2:
            a = int(a) + (1900 if int(a) >= 60 else 2000)
        return f'{a}/{b}'
    t['fy'] = t['fy'].map(full_fy)
    t = t.set_index('fy').astype(float)
    t['total_usd_m'] = t.pop('total_usd') / 1e6

    bt = pd.read_excel(STATS / 'Coffee Exports by Type FY 1991-1992 to FY 2020-2021.xls', header=None)
    years = [str(x).strip() for x in bt.iloc[1, 1:].tolist()]
    split = pd.DataFrame({'robusta_bags': bt.iloc[4, 1:].values, 'arabica_bags': bt.iloc[5, 1:].values}, index=years)
    split = split[split.index.str.match(r'^\d{4}/\d{2}$')].astype(float)
    t = t.join(split)

    tr = pd.read_excel(STATS / "Uganda's Coffee Export Tables for  FY2022-23.xls", sheet_name='Trend', header=None)
    rows = tr.iloc[3:15]
    t.loc['2022/23'] = {'total_bags': rows[5].sum(), 'total_usd_m': rows[6].sum() / 1e6,
                        'robusta_bags': rows[1].sum(), 'arabica_bags': rows[3].sum()}

    m = load_exports_monthly()
    m['fy'] = [coffee_year(p) for p in m.index]
    counts = m.groupby('fy').size()
    later = m.groupby('fy')[['total_bags', 'total_usd_m', 'robusta_bags', 'arabica_bags']].sum(min_count=12)
    later = later[(counts == 12) & (later.index > '2022/23')]
    t = pd.concat([t, later]).sort_index()
    t['source'] = np.where(t.index <= '2021/22', 'annual table', np.where(t.index == '2022/23', 'FY2022/23 tables', 'monthly reports'))
    t['usd_kg'] = t['total_usd_m'] * 1e6 / (t['total_bags'] * BAG_KG)
    return t


# ---------------------------------------------------------------- maize, for comparison
def load_maize_kampala():
    """Retail white maize, Owino market (Kampala), UGX/kg, from WFP."""
    w = pd.read_csv(EXT / 'wfp_food_prices_uga.csv', skiprows=[1])
    w = w[(w['market'] == 'Owino') & (w['commodity'] == 'Maize (white)') & (w['pricetype'] == 'Retail')]
    w['price'] = pd.to_numeric(w['price'], errors='coerce')
    return w.groupby(_period(w['date']))['price'].mean().rename('maize_ugx')


# ---------------------------------------------------------------- coffee-zone climate
def load_zone_climate(last_year=2025):
    """Monthly temperature (ERA5-Land) and rainfall (CHIRPS) for six coffee zones, from
    scripts/gee/uganda_coffee_zones_climate_gee.js. Complete calendar years only."""
    c = pd.read_csv(RAW / 'uganda_coffee_zones_climate.csv')
    return c[c['year'] <= last_year]


def type_climate(c, coffee_type, months):
    """Area-weighted climate of all zones of one coffee type, by calendar year, over the given months:
    mean daily maximum and mean temperature (deg C) and total rainfall (mm)."""
    g = c[(c['type'] == coffee_type) & (c['month'].isin(months))]
    z = g.groupby(['year', 'zone']).agg(tmax=('tmax_c', 'mean'), tmean=('tmean_c', 'mean'),
                                         rain=('rain_chirps_mm', 'sum'), w=('area_km2', 'first')).reset_index()
    return z.groupby('year').apply(lambda x: pd.Series({k: np.average(x[k], weights=x['w']) for k in ['tmax', 'tmean', 'rain']}))


# ---------------------------------------------------------------- global benchmark
GLOBAL = RAW / 'global'
FAO_NAMES = {"Cote d'Ivoire": "Côte d'Ivoire", 'Congo (Kinshasa)': 'Democratic Republic of the Congo',
             'Tanzania': 'United Republic of Tanzania', 'Vietnam': 'Viet Nam', 'China': 'China, mainland'}
AFRICA = ['Uganda', 'Ethiopia', 'Kenya', 'Tanzania', 'Rwanda', 'Burundi', "Cote d'Ivoire", 'Cameroon',
          'Congo (Kinshasa)', 'Madagascar', 'Guinea', 'Togo', 'Sierra Leone', 'Angola', 'Malawi', 'Zambia',
          'Zimbabwe', 'Central African Republic', 'Liberia', 'Ghana', 'Nigeria', 'Gabon', 'Congo (Brazzaville)',
          'Equatorial Guinea', 'Benin']
EAST_AFRICA = ['Uganda', 'Ethiopia', 'Kenya', 'Tanzania', 'Rwanda', 'Burundi']


def load_psd():
    """USDA coffee supply and distribution, wide: one row per country and market year (thousand 60-kg bags)."""
    d = pd.read_csv(GLOBAL / 'psd_coffee.csv')
    return d.pivot_table(index=['Country_Name', 'Market_Year'], columns='Attribute_Description', values='Value').reset_index()


def load_fao_production():
    return pd.read_csv(GLOBAL / 'faostat_coffee_production.csv', low_memory=False)


def load_fao_trade():
    return pd.read_csv(GLOBAL / 'faostat_coffee_trade.csv', low_memory=False)
