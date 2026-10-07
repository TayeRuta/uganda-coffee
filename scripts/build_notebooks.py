"""
Generate the analysis notebooks from source, so their structure stays reviewable in git.

Usage (from anywhere):
    python scripts/build_notebooks.py
    jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
"""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
KERNEL = {'kernelspec': {'display_name': 'Python 3 (ipykernel)', 'language': 'python', 'name': 'python3'},
          'language_info': {'name': 'python'}}

STYLE = r"""
import sys, warnings
sys.path.insert(0, '../scripts')
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from coffee import (load_world, load_fx, load_cpi, load_farmgate, load_exports_monthly, load_exports_annual,
                    load_maize_kampala, coffee_year)

# Ink and grey, with blue for robusta and orange for arabica
INK, GREY, LIGHT, GRID = '#1a1a1a', '#6b6b6b', '#b5b3ad', '#e6e4df'
ROB, ARA = '#2b6c9e', '#c4572e'
plt.rcParams.update({
    'figure.dpi': 110, 'font.size': 10, 'axes.titlesize': 12, 'axes.titleweight': 'medium',
    'axes.titlelocation': 'left', 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#c9c8c4', 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'xtick.color': GREY, 'ytick.color': GREY, 'axes.labelcolor': GREY,
    'legend.frameon': False,
})
pd.set_option('display.width', 200)
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
"""


def notebook(cells, path):
    nb = nbf.v4.new_notebook()
    nb['cells'] = [nbf.v4.new_markdown_cell(c[1].strip()) if c[0] == 'md' else nbf.v4.new_code_cell(c[1].strip())
                   for c in cells]
    nb['metadata'] = KERNEL
    nbf.write(nb, path)
    print('wrote', path.relative_to(ROOT), len(cells), 'cells')


NB1 = [
('md', r"""
# Uganda coffee: exports, world prices and what reaches farmers
**Exports:** Coffee Department (MAAIF, formerly UCDA) annual tables FY1964/65–2022/23, and monthly reports from January 2020, extracted with `scripts/extract_monthly_reports.py`
**Farm-gate prices:** monthly, July 1992 – September 2015 (Coffee Department price table) and January 2020 onwards (monthly reports). The months in between are not published.
**World prices:** IMF monthly robusta and "other mild arabica" prices, via FRED
**Exchange rate and inflation:** UGX per US$ from the Coffee Department table and WFP's conversions; FAO consumer price index

**Questions**
1. How have Uganda's coffee exports changed over six decades?
2. How do Uganda's export prices compare with world benchmarks?
3. How much of the world price reaches farmers, how fast, and does it pass on rises and falls equally?
4. What drove the 2024–25 price boom at the farm gate?
5. When in the year does coffee move, and how risky are coffee prices compared with maize?

**Grades.** *Kiboko* is dried robusta cherry, as most farmers sell it. *FAQ* (fair average quality) is hulled robusta green bean, the form traded for export; hulling removes about half the weight. *Parchment* is washed arabica before hulling; *drugar* is unwashed arabica.

Each finding is written up in a markdown cell directly after the code and output that produced it.
"""),
('md', '## Setup'),
('code', STYLE + r"""
world, fx, cpi = load_world(), load_fx(), load_cpi()
farm, monthly, annual = load_farmgate(), load_exports_monthly(), load_exports_annual()
print('Annual exports:', annual.index[0], '–', annual.index[-1], f'({len(annual)} years)')
print('Monthly exports:', monthly.index.min(), '–', monthly.index.max())
print('Farm-gate FAQ prices:', int(farm['faq_ugx'].notna().sum()), 'months between', farm.index.min(), 'and', farm.index.max())
print('World prices:', world.index.min(), '–', world.index.max())
"""),
('code', r"""
extract = pd.read_csv('../data/processed/monthly_reports_extracted.csv')
corrections = extract[extract['notes'].notna()][['month', 'notes']]
print(f'{len(corrections)} of {len(extract)} monthly reports needed a correction:')
corrections
"""),
('md', r"""
**Data check:** in the 1992–2015 price table, April 2004 appears twice with different prices, and both versions imply farmers were paid more than the world price; both rows are dropped. The table also has some gaps (for example most of 2003–2005), which simply stay missing.

The 80 monthly reports (January 2020 – August 2026) were read automatically. Each report states its figures in a summary sentence and again in tables, and in every month robusta plus arabica now matches the stated total to within 0.2% (bags) and 0.8% (value). The corrections above are typing slips in the reports themselves (a thousands separator written as a full stop, a figure copied from the previous month, a digit swapped). Where the summary sentence and the report's own grade table disagreed, the table was used.

The monthly figures are preliminary. For FY2022/23, where the Coffee Department later published final monthly tables, the reports agree with them to within about 0.2% in most months and 1.6% at most.
"""),

('md', '---\n## 1. Six decades of exports'),
('code', r"""
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
yrs = [int(i[:4]) for i in annual.index]
ax[0].bar(yrs, annual['total_bags'] / 1e6, color=LIGHT, width=0.8)
both = annual.dropna(subset=['robusta_bags'])
by = [int(i[:4]) for i in both.index]
ax[0].bar(by, both['robusta_bags'] / 1e6, color=ROB, width=0.8, label='Robusta')
ax[0].bar(by, both['arabica_bags'] / 1e6, bottom=both['robusta_bags'] / 1e6, color=ARA, width=0.8, label='Arabica')
ax[0].set_ylabel('Million 60-kg bags'); ax[0].set_title('Export volume, by financial year (July–June)'); ax[0].legend()
ax[1].bar(yrs, annual['total_usd_m'] / 1000, color=INK, width=0.8)
ax[1].set_ylabel('US$ billion'); ax[1].set_title('Export value (nominal US$)')
plt.tight_layout(); plt.show()
annual[['total_bags', 'total_usd_m', 'robusta_bags', 'arabica_bags', 'usd_kg', 'source']].tail(12).round(2)
"""),
('md', r"""
**Finding:** for four decades Uganda exported between 2 and 4 million bags a year. Volumes broke out after 2016 and have more than doubled since 2015/16, to a record **8.4 million bags in 2025/26** (preliminary). Value rose even faster: from about US$0.5 billion a year in the late 2010s to **US$2.2 billion in both 2024/25 and 2025/26**, as world prices more than doubled.

Robusta is about 85% of the volume. Arabica's share peaked at a quarter to 30% in 2011–2018 and has since fallen back as robusta planting expanded.

The 1970s value spike (1976/77) came from the world price surge after Brazil's 1975 frost. Values are in nominal dollars, so long-run comparisons of value overstate real growth.
"""),

('md', '---\n## 2. Uganda\'s export prices against world benchmarks'),
('code', r"""
e = monthly.join(world, rsuffix='_world')
e['robusta_vs_world'] = e['robusta_usd_kg'] / e['robusta_usd_kg_world']
e['arabica_vs_world'] = e['arabica_usd_kg'] / e['arabica_usd_kg_world']
fig, ax = plt.subplots(figsize=(11, 3.8))
t = e.index.to_timestamp()
ax.plot(t, e['robusta_usd_kg_world'], color=ROB, lw=1.4, ls='--', label='World robusta')
ax.plot(t, e['robusta_usd_kg'], color=ROB, lw=2.2, label='Uganda robusta exports')
ax.plot(t, e['arabica_usd_kg_world'], color=ARA, lw=1.4, ls='--', label='World arabica (other milds)')
ax.plot(t, e['arabica_usd_kg'], color=ARA, lw=2.2, label='Uganda arabica exports')
ax.set_ylabel('US$ per kg'); ax.set_title('Export prices follow the world benchmarks'); ax.legend(ncol=2, fontsize=9)
plt.tight_layout(); plt.show()
e.groupby(e.index.year)[['robusta_vs_world', 'arabica_vs_world']].mean().round(2)
"""),
('md', r"""
**Finding:** Uganda's robusta sells close to the world robusta price, at 82–100% of it (about 92% on average). Its arabica sells at about 65–85% of the "other milds" benchmark, which is set by washed arabica from Colombia and Central America. Much of Uganda's arabica is unwashed *drugar*, which trades below washed coffee, so the arabica discount is partly a quality and processing gap that washing stations could narrow.
"""),

('md', '---\n## 3. How much of the world price reaches farmers?'),
('code', r"""
d = farm.join(world).join(fx)
d['faq_usd'] = d['faq_ugx'] / d['ugx_per_usd']
d['farmer_share_faq'] = d['faq_usd'] / d['robusta_usd_kg']
d['kiboko_to_faq'] = d['kiboko_ugx'] / d['faq_ugx']
share = d.groupby(d.index.year)[['farmer_share_faq', 'kiboko_to_faq']].mean()
fig, ax = plt.subplots(figsize=(11, 3.6))
s = d['farmer_share_faq']
ax.plot(s.index.to_timestamp(), 100 * s, color=INK, lw=1.2, alpha=.5)
ax.plot(share.index.map(lambda y: pd.Timestamp(f'{y}-07-01')), 100 * share['farmer_share_faq'], color=INK, lw=2.4, marker='o', ms=3)
ax.axvspan(pd.Timestamp('2015-10-01'), pd.Timestamp('2019-12-31'), color=GRID, lw=0)
ax.text(pd.Timestamp('2017-11-01'), 50, 'not\npublished', ha='center', color=GREY, fontsize=9)
ax.set_ylabel('% of world robusta price'); ax.set_ylim(30, 100)
ax.set_title('Farm-gate FAQ price as a share of the world robusta price (yearly average in bold)')
plt.tight_layout(); plt.show()
share.round(2).T
"""),
('md', r"""
**Finding:** farmers selling FAQ received about **42–46% of the world robusta price in 1992–93**, just after Uganda liberalised coffee marketing, rising to **65–72% for most of 2000–2015** and **72–83% in 2022–2026**. The share dips when world prices crash (52% in 2001), because traders' and exporters' costs don't fall with the price.

The kiboko price stays close to half the FAQ price throughout (ratio 0.38–0.51), matching the weight lost in hulling. Farmers selling kiboko are therefore paid about the same per kg of coffee as FAQ sellers: the difference is the hulling, not the price.
"""),
('code', r"""
d['world_rob_ugx'] = d['robusta_usd_kg'] * d['ugx_per_usd']
d['world_ara_ugx'] = d['arabica_usd_kg'] * d['ugx_per_usd']

def passthrough(frame, farm_col, world_col, lags=3):
    x = pd.DataFrame({'f': np.log(frame[farm_col]), 'w': np.log(frame[world_col])})
    dx = x.diff()
    X = pd.concat({f'w_l{k}': dx['w'].shift(k) for k in range(lags + 1)}, axis=1)
    X['gap'] = (x['f'] - x['w']).shift(1)   # last month's farm-gate to world gap
    j = pd.concat([dx['f'].rename('df'), X], axis=1).dropna()
    m = sm.OLS(j['df'], sm.add_constant(j.drop(columns='df'))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    j2 = j.assign(rise=j['w_l0'].clip(lower=0), fall=j['w_l0'].clip(upper=0)).drop(columns='w_l0')
    m2 = sm.OLS(j2['df'], sm.add_constant(j2.drop(columns='df'))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    return {'months': int(m.nobs), 'same_month': m.params['w_l0'], 'same_month_se': m.bse['w_l0'],
            'gap_closed_per_month': -m.params['gap'], 'half_life_months': np.log(0.5) / np.log(1 + m.params['gap']),
            'rises': m2.params['rise'], 'falls': m2.params['fall'],
            'rise_vs_fall_p': float(m2.t_test('rise = fall').pvalue)}

rows = []
for period, sl in [('1992–2015', slice('1992-07', '2015-09')), ('2020–2026', slice('2020-01', '2026-08'))]:
    for label, fc, wc in [('Robusta FAQ', 'faq_ugx', 'world_rob_ugx'), ('Robusta kiboko', 'kiboko_ugx', 'world_rob_ugx'),
                          ('Arabica parchment', 'parchment_ugx', 'world_ara_ugx')]:
        rows.append({'period': period, 'grade': label, **passthrough(d.loc[sl], fc, wc)})
pt = pd.DataFrame(rows)
pt.round(2)
"""),
('md', r"""
**Reading the table:** `same_month` is the share of a world price change (in shillings) that shows up in the farm-gate price within the same month. `gap_closed_per_month` is how fast any remaining gap between farm-gate and world prices closes afterwards, and `half_life_months` converts that into the time to close half of it. `rises` and `falls` split the same-month response by direction.

**Finding:** robusta prices respond fast. About **two-thirds or more of a world price change reaches robusta farmers in the same month** (0.65–0.79), and the rest closes by about a fifth each month, a half-life of two to three months. With 80-plus licensed exporters competing for coffee, the market passes prices through quickly.

**Arabica responds more slowly**: about 40% in the same month, with the remaining gap closing slowly, especially since 2020. Arabica moves through cooperatives and washing stations, and its price depends more on quality, so it tracks the benchmark less tightly.

**Rises and falls:** in 2020–2026, world price *rises* reached robusta farmers almost in full in the same month, while *falls* were passed on by only about half (p = 0.06 for FAQ and 0.30 for kiboko; not significant for 1992–2015). That's the opposite of the common worry that traders pass on falls faster than rises, and fits strong buyer competition during the recent boom. With one boom and one partial fall in the data, it is suggestive only.
"""),

('md', '---\n## 4. What drove the 2024–25 farm-gate boom?'),
('code', r"""
d['farmer_share'] = d['faq_ugx'] / d['world_rob_ugx']
rows = []
for a, b in [('2020', '2025'), ('2020', '2026')]:
    A, B = d.loc[a].mean(numeric_only=True), d.loc[b].mean(numeric_only=True)
    total = np.log(B['faq_ugx'] / A['faq_ugx'])
    parts = {'world price (US$)': np.log(B['robusta_usd_kg'] / A['robusta_usd_kg']),
             'exchange rate': np.log(B['ugx_per_usd'] / A['ugx_per_usd']),
             "farmers' share": np.log(B['farmer_share'] / A['farmer_share'])}
    rows.append({'from': a, 'to': b, 'FAQ price, UGX/kg': f"{A['faq_ugx']:,.0f} → {B['faq_ugx']:,.0f}",
                 'multiple': np.exp(total), **{k + ' (% of rise)': 100 * v / total for k, v in parts.items()}})
pd.DataFrame(rows).round(2)
"""),
('code', r"""
fig, ax = plt.subplots(figsize=(11, 3.8))
z = d.loc['2019-06':]
ax.plot(z.index.to_timestamp(), z['world_rob_ugx'], color=ROB, lw=1.6, ls='--', label='World robusta, in UGX/kg')
ax.plot(z.index.to_timestamp(), z['faq_ugx'], color=INK, lw=2.4, label='Farm-gate FAQ, UGX/kg')
ax.plot(z.index.to_timestamp(), z['kiboko_ugx'], color=GREY, lw=2, label='Farm-gate kiboko, UGX/kg')
peak = z['faq_ugx'].idxmax()
ax.annotate(f"FAQ peak {z.loc[peak, 'faq_ugx']:,.0f} ({peak.strftime('%b %Y')})", (peak.to_timestamp(), z.loc[peak, 'faq_ugx']),
            xytext=(-12, -4), textcoords='offset points', ha='right', va='top', fontsize=9, color=INK)
ax.set_ylabel('UGX per kg'); ax.set_title('The farm-gate boom tracked the world price'); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
latest = d['faq_ugx'].dropna().index[-1]
print(f"FAQ: peak {d['faq_ugx'].max():,.0f} ({d['faq_ugx'].idxmax()}), latest {d.loc[latest, 'faq_ugx']:,.0f} ({latest}): "
      f"{100 * (d.loc[latest, 'faq_ugx'] / d['faq_ugx'].max() - 1):.0f}% from peak")
print(f"World robusta: peak US${world['robusta_usd_kg'].max():.2f}/kg ({world['robusta_usd_kg'].idxmax()}), "
      f"latest US${world['robusta_usd_kg'].iloc[-1]:.2f} ({world.index[-1]}): {100 * (world['robusta_usd_kg'].iloc[-1] / world['robusta_usd_kg'].max() - 1):.0f}%")
"""),
('md', r"""
**Finding:** robusta farm-gate prices rose about **3.4 times** from 2020 to 2025, from about UGX 4,000 to over 13,000 per kg of FAQ. **Almost all of it (about 96%) came from the world price**, which more than tripled after drought hit Vietnam and Brazil. The shilling was stable against the dollar, and farmers' share of the world price rose only a little.

Both peaked in **February 2025**. Since then farm-gate FAQ is down about a quarter and the world price about 30%. For anyone lending against coffee income, the lesson is that Ugandan farm-gate prices are essentially the world price with a lag of a few months: the boom was not a local shift, and it is already partly unwinding.
"""),

('md', '---\n## 5. Timing and risk'),
('code', r"""
s = monthly.loc['2020-07':'2026-06'].copy()
s['fy'] = [coffee_year(p) for p in s.index]
calendar = pd.DataFrame({t: s.groupby('fy')[f'{t}_bags'].transform(lambda x: 100 * x / x.sum()).groupby(s.index.month).mean()
                         for t in ['robusta', 'arabica']})
calendar.index = MON
fig, ax = plt.subplots(figsize=(9, 3.4))
xx = np.arange(12)
ax.bar(xx - 0.2, calendar['robusta'], width=0.4, color=ROB, label='Robusta')
ax.bar(xx + 0.2, calendar['arabica'], width=0.4, color=ARA, label='Arabica')
ax.axhline(100 / 12, color=GREY, lw=1, ls='--'); ax.set_xticks(xx); ax.set_xticklabels(MON)
ax.set_ylabel('% of the year\'s exports'); ax.set_title('When coffee leaves Uganda (average, FY2020/21–2025/26)'); ax.legend()
plt.tight_layout(); plt.show()
calendar.round(1).T
"""),
('md', r"""
**Finding:** robusta exports peak in **June–September** (about 11% of the year's volume each month), following the main harvest in Greater Masaka and the southwest; a smaller wave follows the central region's harvest around the turn of the year. Arabica peaks in **February–May** (about 12% a month), after the Mt Elgon harvest is processed. These are the months when farmers' coffee income arrives, and when loan repayment schedules tied to coffee should fall.
"""),
('code', r"""
mz = load_maize_kampala()
real = pd.DataFrame({'Robusta FAQ': farm['faq_ugx'], 'Robusta kiboko': farm['kiboko_ugx'],
                     'Arabica parchment': farm['parchment_ugx'], 'Maize, Kampala retail': mz}).div(cpi, axis=0)
rows = []
for label, sl in [('2011–2015', slice('2011-04', '2015-09')), ('2020–2026', slice('2020-01', '2026-03'))]:
    x = np.log(real.loc[sl])
    for c in real.columns:
        rows.append({'period': label, 'price': c, 'typical monthly move (%)': 100 * x[c].diff().std(),
                     'typical 12-month move (%)': 100 * x[c].diff(12).std()})
vol = pd.DataFrame(rows).pivot(index='price', columns='period')
worst = pd.DataFrame({c: {'worst 12-month real fall (%)': 100 * (np.exp(np.log(real[c]).diff(12).min()) - 1),
                          'when': str(np.log(real[c]).diff(12).idxmin())} for c in real.columns}).T
display(vol.round(1)); worst
"""),
('md', r"""
**Finding:** month to month, coffee prices are **calmer than maize**: real robusta and arabica prices typically move about 7–10% a month, against 14–18% for maize in Kampala. Coffee's risk is in long cycles instead. Over 12 months, coffee prices swing about as much as maize, and the worst real falls are deeper: **52% for robusta FAQ and 64% for kiboko (to 2001)** and 57% for arabica parchment (to 2012), against 46% for maize.

For lenders and farmers this means coffee income is fairly predictable within a season but can halve over a year or two when the world cycle turns, as it partly has since February 2025.
"""),

('md', '---\n## Export'),
('code', r"""
from pathlib import Path
out = Path('../data/processed')
annual.round(4).to_csv(out / 'exports_annual.csv')
pt.round(4).to_csv(out / 'price_passthrough.csv', index=False)
share.round(4).to_csv(out / 'farmer_share_by_year.csv')
calendar.round(2).to_csv(out / 'export_calendar.csv')
vol.round(2).to_csv(out / 'price_volatility.csv')
d[['faq_ugx', 'kiboko_ugx', 'parchment_ugx', 'robusta_usd_kg', 'arabica_usd_kg', 'ugx_per_usd', 'farmer_share_faq']].round(4).to_csv(out / 'farmgate_and_world_monthly.csv')
print('Saved 6 tables to data/processed/')
"""),
('md', r"""
---
## Summary

- **Exports have more than doubled since 2015/16**, to a record 8.4 million bags in 2025/26, worth about US$2.2 billion a year in 2024/25 and 2025/26.
- **Uganda's robusta sells at about the world price; its arabica at about 65–85% of the washed-arabica benchmark**, partly because much of it is unwashed.
- **Farmers' share of the world robusta price rose from about 45% after liberalisation to 70–80% today.**
- **Prices pass through fast:** about two-thirds of a world price change reaches robusta farmers within the month, the rest within a few months. Arabica is slower.
- **The 2024–25 boom was the world price**, almost entirely. Farm-gate prices peaked in February 2025 and are down about a quarter since.
- **Coffee income arrives June–September (robusta) and February–May (arabica).** Prices are calmer than maize month to month, but can halve over a year when the world cycle turns.

**Caveats**
- Farm-gate prices for late 2015–2019 are not published, so the two periods are analysed separately where it matters.
- Monthly export figures are preliminary and differ from final figures by up to about 2%.
- Nominal US$ values overstate real long-run growth.

**Next steps**
1. Climate exposure: rainfall and temperature in arabica and robusta zones against the following year's exports.
2. Deforestation screening of coffee areas for the EU regulation.
"""),
]

NB2 = [
('md', r"""
# Coffee and climate: warming zones and what heat and rain do to exports
**Climate:** monthly ERA5-Land temperature (mean, daily maximum, daily minimum; about 11 km) and CHIRPS rainfall (about 5.5 km) for six coffee zones, January 1990 – December 2025, exported with `scripts/gee/uganda_coffee_zones_climate_gee.js`
**Exports:** robusta and arabica export volumes by financial year (notebook 01), FY1991/92–2025/26

| Zone | Type | Land included |
|---|---|---|
| Mt Elgon | Arabica | Elgon coffee districts, 1,300 m or higher |
| Rwenzori | Arabica | Rwenzori coffee districts, 1,300 m or higher |
| Greater Masaka, Central, South-west, Busoga | Robusta | each group's coffee districts, below 1,500 m |

**Questions**
1. Are Uganda's coffee zones warming, and how often are months now unusually hot?
2. Has rainfall changed?
3. Does a year's heat or rainfall show up in the following exports?

**Timing.** Exports for financial year *y*/*y*+1 (July–June) come mostly from the crop that flowered and filled during calendar year *y*. Climate in year *y*, and in the second half of year *y*−1 (when the next season's flower buds form), is therefore matched to exports in FY *y*/*y*+1.

Each finding is written up in a markdown cell directly after the code and output that produced it.
"""),
('md', '## Setup and data checks'),
('code', STYLE + r"""
from scipy import stats
from coffee import load_zone_climate, type_climate
rng = np.random.default_rng(42)
c = load_zone_climate()
zones = c.groupby('zone').agg(type=('type', 'first'), area_km2=('area_km2', 'first'), months=('date', 'size'),
                              mean_temp_c=('tmean_c', 'mean'), mean_daily_max_c=('tmax_c', 'mean'),
                              annual_rain_mm=('rain_chirps_mm', lambda x: x.sum() / c['year'].nunique()))
print(c['date'].min(), '–', c['date'].max(), '| missing values:', int(c.isna().sum().sum()))
zones.round(1)
"""),
('md', r"""
**Check:** all six zones have all 432 months from 1990 to 2025, with no gaps. The arabica zones average about 17–18 °C and the robusta zones 21–22 °C, which matches where each type grows best. Annual rainfall ranges from about 1,000 mm (South-west) to about 1,640 mm (Mt Elgon).
"""),

('md', '---\n## 1. Warming'),
('code', r"""
annual = c.groupby(['zone', 'year']).agg(tmean=('tmean_c', 'mean'), tmax=('tmax_c', 'mean'), tmin=('tmin_c', 'mean'),
                                          rain=('rain_chirps_mm', 'sum'))
rows = []
for z, g in annual.groupby(level=0):
    g = g.droplevel(0)
    r = {'zone': z}
    for v in ['tmean', 'tmax', 'tmin', 'rain']:
        m = sm.OLS(g[v].values, sm.add_constant(np.array(g.index, float))).fit(cov_type='HAC', cov_kwds={'maxlags': 2})
        r[f'{v} per decade'] = 10 * m.params[1]
        r[f'{v} p'] = m.pvalues[1]
    r['daily max, 1990s'] = g.loc[1990:1999, 'tmax'].mean()
    r['daily max, 2016–25'] = g.loc[2016:2025, 'tmax'].mean()
    rows.append(r)
trends = pd.DataFrame(rows).set_index('zone')
trends.round(3)
"""),
('code', r"""
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8), sharey=False)
for z, g in annual.groupby(level=0):
    g = g.droplevel(0)
    col = ARA if 'Arabica' in z else ROB
    a = ax[0] if 'Robusta' in z else ax[1]
    a.plot(g.index, g['tmax'] - g.loc[1991:2020, 'tmax'].mean(), color=col, lw=1.6, alpha=.85, label=z.split(', ')[1])
for a, t in zip(ax, ['Robusta zones', 'Arabica zones']):
    a.axhline(0, color=GREY, lw=1); a.set_title(t); a.legend(fontsize=8.5, ncol=2)
ax[0].set_ylabel('Daily maximum vs 1991–2020 (°C)')
plt.tight_layout(); plt.show()
"""),
('md', r"""
**Finding:** every coffee zone has warmed significantly since 1990. The robusta zones are warming fastest: average temperature by 0.3–0.44 °C per decade and **daytime highs by 0.43–0.67 °C per decade**. Central and Greater Masaka were 1.6–1.7 °C hotter in the daytime in 2016–25 than in the 1990s. The arabica zones on Mt Elgon and the Rwenzoris are warming more slowly, by about 0.2 °C per decade.

**Caution:** these trends come from ERA5-Land, a reanalysis that blends weather models with observations. Reanalysis trends in data-sparse regions can be exaggerated by changes in the observations it draws on, and clearing of trees and wetlands raises local daytime highs. The direction is consistent with other evidence of warming in East Africa, but the size of the robusta-zone trend should be checked against weather-station records before it is used for planning.
"""),
('code', r"""
c['p90'] = c.groupby(['zone', 'month'])['tmax_c'].transform(
    lambda s: s[c.loc[s.index, 'year'].between(1991, 2020)].quantile(0.9))
c['hot'] = c['tmax_c'] > c['p90']
c['decade'] = (c['year'] // 10 * 10).astype(str) + 's'
hot = 100 * c.groupby(['zone', 'decade'])['hot'].mean().unstack()
hot.round(0)
"""),
('md', r"""
**Finding:** a "hot month" here is one whose daytime highs exceed the hottest tenth of that calendar month in 1991–2020, so about 10% of months would be hot if nothing were changing. In the 1990s almost none were. In the 2020s so far, **44–46% of months in Central and Greater Masaka** have been hot, and about a quarter in Busoga and the South-west. The arabica zones have changed less (6–21%).
"""),

('md', '---\n## 2. Rainfall'),
('code', r"""
trends[['rain per decade', 'rain p']].round(3)
"""),
('md', r"""
**Finding:** rainfall has not fallen in any coffee zone. It has risen significantly on **Mt Elgon (about +108 mm per decade)** and in **Busoga (about +78 mm per decade)**, consistent with the wetting of the east found in the rainfall project. Elsewhere the changes are small and not significant. In the coffee belt, the climate change that is clearly under way is heat, not drought.
"""),

('md', '---\n## 3. Do heat and rain show up in exports?'),
('code', r"""
ann = load_exports_annual().dropna(subset=['robusta_bags'])
ann.index = [int(i[:4]) for i in ann.index]
rows = []
for t, col in [('robusta', 'robusta_bags'), ('arabica', 'arabica_bags')]:
    y = np.log(ann[col])
    for window, months in [('Jan–Jun', range(1, 7)), ('Jul–Dec', range(7, 13)), ('calendar year', range(1, 13))]:
        clim = type_climate(c, t, months)
        for lag in [0, 1]:
            d = pd.DataFrame({'y': y}).join(clim.rename(index=lambda i: i + lag)).dropna()
            X = pd.DataFrame({'rain': (d['rain'] - d['rain'].mean()) / d['rain'].std(),
                              'heat': (d['tmax'] - d['tmax'].mean()) / d['tmax'].std(),
                              'trend': d.index - d.index.min()}, index=d.index)
            m = sm.OLS(d['y'], sm.add_constant(X)).fit(cov_type='HAC', cov_kwds={'maxlags': 2})
            rows.append({'type': t, 'climate months': window, 'climate year': 'same year' if lag == 0 else 'year before',
                         'wetter +1 SD (%)': 100 * (np.exp(m.params['rain']) - 1), 'p rain': m.pvalues['rain'],
                         'hotter +1 SD (%)': 100 * (np.exp(m.params['heat']) - 1), 'p heat': m.pvalues['heat'], 'years': int(m.nobs)})
grid = pd.DataFrame(rows)
grid.round(3)
"""),
('md', r"""
**Reading the table:** each row relates export volume (logged, with a linear trend) to rainfall and daytime heat in the coffee zones over the given months, either in the same calendar year as the crop or the year before. Effects are per standard deviation of that climate variable. Twelve combinations were tried per coffee type, so single p-values near 0.05 should not be over-read.

**Finding:** two signals stand out for **robusta**, and no consistent one for arabica:
- **Heat in January–June of the crop year lowers robusta exports**, by about 20% per standard deviation (p < 0.001). This is when robusta flowers after the dry season and sets fruit; heat stress then is known to cause flower and berry drop.
- **A wetter July–December in the year before raises robusta exports**, by about 14% per standard deviation (p = 0.004), when the flower buds for the next crop form.

**Arabica** shows no consistent signal. One of its twelve combinations reaches p < 0.05 (calendar-year heat, +9%, in the opposite direction to robusta), which is about what chance alone would produce across twelve tries. Arabica exports depend heavily on processing, stocks and quality, and the arabica zones have warmed less.
"""),
('code', r"""
y = np.log(ann['robusta_bags'])
heat = type_climate(c, 'robusta', range(1, 7))['tmax']
wet_before = type_climate(c, 'robusta', range(7, 13))['rain'].rename(index=lambda i: i + 1)
d = pd.DataFrame({'y': y, 'heat': heat, 'rain': wet_before}).dropna()

# 1) Year-to-year changes: removes any trend, linear or not
dd = d.diff().dropna()
dd['heat_sd'] = dd['heat'] / d['heat'].std()
dd['rain_sd'] = dd['rain'] / d['rain'].std()
m = sm.OLS(dd['y'], sm.add_constant(dd[['heat_sd', 'rain_sd']])).fit(cov_type='HAC', cov_kwds={'maxlags': 2})
rows = []
for v in ['heat_sd', 'rain_sd']:
    null = [sm.OLS(dd['y'], sm.add_constant(dd[['heat_sd', 'rain_sd']].assign(**{v: rng.permutation(dd[v].values)}))).fit().params[v]
            for _ in range(2000)]
    rows.append({'check': 'year-to-year changes, 1992–2025', 'climate': 'Jan–Jun heat' if v == 'heat_sd' else 'Jul–Dec rain, year before',
                 'effect per SD (%)': 100 * (np.exp(m.params[v]) - 1), 'p': m.pvalues[v],
                 'permutation p': (np.sum(np.abs(null) >= abs(m.params[v])) + 1) / 2001})

# 2) Before the export boom: 1991–2014 only
q = d.loc[:2014]
X = pd.DataFrame({'heat_sd': (q['heat'] - q['heat'].mean()) / q['heat'].std(),
                  'rain_sd': (q['rain'] - q['rain'].mean()) / q['rain'].std(), 'trend': q.index - q.index.min()}, index=q.index)
m2 = sm.OLS(q['y'], sm.add_constant(X)).fit()
for v, lab in [('heat_sd', 'Jan–Jun heat'), ('rain_sd', 'Jul–Dec rain, year before')]:
    rows.append({'check': 'levels with trend, 1991–2014 only', 'climate': lab,
                 'effect per SD (%)': 100 * (np.exp(m2.params[v]) - 1), 'p': m2.pvalues[v], 'permutation p': np.nan})
robust = pd.DataFrame(rows)
robust.round(3)
"""),
('md', r"""
**Finding:** both robusta effects survive the stricter checks.
- Comparing **year-to-year changes** removes any trend, straight or curved, so the effects can't come from heat and exports both rising over time. Heat still lowers exports (about 9% per standard deviation, permutation p ≈ 0.04), and the previous year's rain still raises them (about 7%, permutation p ≈ 0.02).
- Using only **1991–2014**, before the export boom, gives similar or larger effects (heat about −16%, rain about +12%, both p ≈ 0.01).

**Confidence: medium.** The effects are consistent across checks and biologically plausible, but they rest on 34 years of national exports, which also reflect stocks and trade timing, and several windows were tried.

**What it means:** the robusta belt is warming fastest exactly in the months when heat hurts the crop. Uganda's rising exports have come from new planting and strong prices, which so far have outweighed the climate drag. Heat-tolerant varieties, shade trees and mulching in the Central and Masaka robusta zones are the adaptation priorities this points to.
"""),

('md', '---\n## Export'),
('code', r"""
from pathlib import Path
out = Path('../data/processed')
trends.round(4).to_csv(out / 'zone_climate_trends.csv')
hot.round(2).to_csv(out / 'hot_months_by_decade.csv')
grid.round(4).to_csv(out / 'climate_export_grid.csv', index=False)
robust.round(4).to_csv(out / 'climate_export_robustness.csv', index=False)
annual.round(3).to_csv(out / 'zone_climate_annual.csv')
print('Saved 5 tables to data/processed/')
"""),
('md', r"""
---
## Summary

- **All coffee zones are warming.** The robusta zones fastest: daytime highs up about 0.4–0.7 °C per decade; Central and Greater Masaka were 1.6–1.7 °C hotter in 2016–25 than in the 1990s. In the 2020s close to half of all months there have been unusually hot.
- **Rainfall has not fallen;** it has risen on Mt Elgon and in Busoga. Heat, not drought, is the trend.
- **Heat in January–June cuts robusta exports** (about 9–20% per standard deviation, depending on the check), and **a wet second half of the year lifts the next year's robusta crop** (about 7–14%). *Medium confidence.*
- **Arabica shows no consistent climate signal** in national exports.

**Caveats:** reanalysis temperature trends need checking against stations; national exports are a noisy measure of the harvest; twelve season windows were tried per coffee type.

**Next:** deforestation screening of coffee areas for the EU regulation, and a station-data check of the warming trend.
"""),
]

NB3 = [
('md', r"""
# Uganda's coffee against the world: a benchmark
**Sources:** USDA Foreign Agricultural Service coffee supply and distribution (PSD), all producing countries, market years to 2025/26; FAOSTAT green coffee area, yield, production and trade, to 2024; IMF world prices; Uganda's Coffee Department.

**How peers are chosen (by rule, not by hand)**
- **World:** every country with at least 1% of world production, 2021–2025 average (USDA).
- **Africa:** every African producer above 100,000 bags a year.
- **Like-for-like groups:** countries are grouped by what they grow, using USDA's robusta and arabica split: *robusta-led* (70% or more robusta), *arabica-led* (30% or less), *mixed* (in between). Comparisons that depend on the type of coffee (yield, price) are made within groups or adjusted for the mix.

**Metrics** follow what USDA and the International Coffee Organization report: production and exports in 60-kg bags, share of world exports, growth, domestic consumption, yield per hectare, export price realisation, and production volatility. Every metric carries the quality of its underlying data.

Each finding is written up in a markdown cell directly after the code and output that produced it.
"""),
('md', '## Setup'),
('code', STYLE + r"""
from coffee import load_psd, load_fao_production, load_fao_trade, FAO_NAMES, AFRICA, EAST_AFRICA, BAG_KG
psd = load_psd()
fao_p, fao_t = load_fao_production(), load_fao_trade()
world = load_world()
print('USDA market years:', psd['Market_Year'].min(), '–', psd['Market_Year'].max(), '|', psd['Country_Name'].nunique(), 'countries')
print('FAOSTAT years:', fao_p['Year'].min(), '–', fao_p['Year'].max())
"""),

('md', '---\n## 1. Who are the peers?'),
('code', r"""
RECENT = range(2021, 2026)   # USDA market years 2021/22 – 2025/26
cols = ['Production', 'Arabica Production', 'Robusta Production', 'Exports', 'Domestic Consumption']
rec = psd[psd['Market_Year'].isin(RECENT)].groupby('Country_Name')[cols].mean()
rec = rec[rec['Production'] > 0]
rec['world_production_share'] = 100 * rec['Production'] / rec['Production'].sum()
rec['world_export_share'] = 100 * rec['Exports'] / rec['Exports'].sum()
rec['robusta_share'] = 100 * rec['Robusta Production'] / rec['Production']
rec['consumed_at_home'] = 100 * rec['Domestic Consumption'] / rec['Production']
rec['production_rank'] = rec['Production'].rank(ascending=False).astype(int)
rec['export_rank'] = rec['Exports'].rank(ascending=False).astype(int)
rec['group'] = np.select([rec['robusta_share'] >= 70, rec['robusta_share'] <= 30], ['Robusta-led', 'Arabica-led'], 'Mixed')
rec['africa'] = rec.index.isin(AFRICA)

world_peers = rec[rec['world_production_share'] >= 1].index
africa_peers = rec[rec['africa'] & (rec['Production'] >= 100)].index
peers = rec.loc[sorted(set(world_peers) | set(africa_peers), key=lambda c: -rec.loc[c, 'Production'])].copy()
peers['set'] = np.where(peers.index.isin(world_peers) & peers['africa'], 'World and Africa',
                        np.where(peers.index.isin(world_peers), 'World', 'Africa'))
print(f'{len(world_peers)} world peers, {len(africa_peers)} African peers, {len(peers)} in total')
peers[['set', 'group', 'Production', 'Exports', 'world_production_share', 'world_export_share', 'production_rank', 'export_rank', 'robusta_share', 'consumed_at_home']].round(1)
"""),
('md', r"""
**Finding:** the rule gives 13 world peers and 11 African peers (22 countries in all, with Ethiopia and Uganda in both sets). **Uganda is the world's 6th-largest producer and 6th-largest exporter**, with about 4.6% of world exports, and **Africa's largest exporter**. Ethiopia produces more but drinks about 40% of its own crop; Uganda consumes only about 4% at home, so almost everything it grows is exported.

Uganda is *robusta-led* (about 84% robusta), alongside Vietnam, Indonesia and India and the West and Central African robusta producers. Its arabica (about 1 million bags) is best compared with the East African arabica producers.
"""),

('md', '---\n## 2. Growth'),
('code', r"""
prod = psd.pivot_table(index='Market_Year', columns='Country_Name', values='Production')
exp_ = psd.pivot_table(index='Market_Year', columns='Country_Name', values='Exports')
growth = pd.DataFrame({
    'production growth, % a year': 100 * ((prod.loc[2021:2025].mean() / prod.loc[2006:2010].mean()) ** (1 / 15) - 1),
    'export growth, % a year': 100 * ((exp_.loc[2021:2025].mean() / exp_.loc[2006:2010].mean()) ** (1 / 15) - 1),
}).loc[peers.index]
growth['group'] = peers['group']
growth.sort_values('production growth, % a year', ascending=False).round(1)
"""),
('code', r"""
top = ['Brazil', 'Vietnam', 'Colombia', 'Indonesia', 'Ethiopia', 'Uganda', 'India']
fig, ax = plt.subplots(figsize=(10, 4))
for c in top:
    s = prod[c].loc[1990:2025] / 1000
    ax.plot(s.index, s.values, lw=2.6 if c == 'Uganda' else 1.4, color=INK if c == 'Uganda' else LIGHT)
    ax.annotate(c, (s.index[-1], s.values[-1]), xytext=(4, 0), textcoords='offset points', fontsize=8.5,
                color=INK if c == 'Uganda' else GREY, va='center')
ax.set_yscale('log'); ax.set_ylabel('Million 60-kg bags (log scale)')
ax.set_title('Production of the largest producers (USDA)'); plt.tight_layout(); plt.show()
"""),
('md', r"""
**Finding:** comparing 2021–25 with 2006–10, **Uganda's production grew about 5% a year, the fastest of the ten largest producers** (among all peers only China, from a much smaller base, grew faster). Brazil and Colombia grew about 1.5–2% a year; several West and Central African robusta producers shrank (Côte d'Ivoire, Cameroon, Guinea and Madagascar, by about 4–7% a year). Uganda has moved from being one of many African robusta producers to being in a class of its own on the continent.
"""),

('md', '---\n## 3. Yield: the biggest gap, and the least certain number'),
('code', r"""
def fao_name(c):
    return FAO_NAMES.get(c, c)

rows = []
for c in peers.index:
    q = fao_p[(fao_p['Area'] == fao_name(c)) & fao_p['Year'].between(2020, 2024)]
    area, yld = q[q['Element'] == 'Area harvested'], q[q['Element'] == 'Yield']
    official = (area['Flag'] == 'A').mean() if len(area) else np.nan
    rows.append({'country': c, 'group': peers.loc[c, 'group'], 'yield, kg/ha': yld['Value'].mean(),
                 'area figures official (%)': 100 * official,
                 'data quality': 'official' if official == 1 else ('partly estimated' if official > 0 else 'estimated or imputed')})
yields = pd.DataFrame(rows).set_index('country')
yields.sort_values(['group', 'yield, kg/ha'], ascending=[True, False]).round(0)
"""),
('md', r"""
**Finding:** among robusta-led producers with official area data, **Vietnam harvests about 2,900 kg of green coffee per hectare; India and Indonesia 600–750**. FAOSTAT puts Uganda at about **560 kg/ha, a gap of roughly five times to Vietnam**.

**But Uganda's yield is the least certain number in this benchmark.** FAOSTAT's harvested area for Uganda is imputed in every year from 2020 to 2024, so its yield is a production figure divided by an estimated area. Uganda's coffee is also largely smallholder and intercropped with bananas and food crops, which makes "area" itself hard to define. The direction of the gap is not in doubt (Vietnam's intensive, irrigated, fertilised monoculture is in a different league), but its size is. A measured yield survey is the single most valuable missing data point for Uganda's coffee sector.
"""),

('md', '---\n## 4. Price: is Uganda paid fairly for what it sells?'),
('code', r"""
w20 = world.loc['2020':'2024'].mean()
rows = []
for c in peers.index:
    t = fao_t[(fao_t['Area'] == fao_name(c))]
    yrs = [f'Y{y}' for y in range(2020, 2025)]
    q = t[t['Element'] == 'Export quantity'][yrs].sum(axis=1)
    v = t[t['Element'] == 'Export value'][yrs].sum(axis=1)
    if not len(q) or q.iloc[0] <= 0:
        continue
    price = float(v.iloc[0] / q.iloc[0])            # 1000 US$ per tonne = US$ per kg
    r = peers.loc[c, 'robusta_share'] / 100
    reference = r * w20['robusta_usd_kg'] + (1 - r) * w20['arabica_usd_kg']
    rows.append({'country': c, 'group': peers.loc[c, 'group'], 'export price, US$/kg': price,
                 'mix reference, US$/kg': reference, 'price realisation (%)': 100 * price / reference})
prices = pd.DataFrame(rows).set_index('country')
print(f"World reference prices 2020–24: robusta US${w20['robusta_usd_kg']:.2f}/kg, arabica (other milds) US${w20['arabica_usd_kg']:.2f}/kg")
prices.sort_values(['group', 'price realisation (%)'], ascending=[True, False]).round(2)
"""),
('md', r"""
**Reading the table:** each country's average export price (FAOSTAT export value ÷ quantity, 2020–2024) is compared with what its mix of coffee would fetch at world reference prices (its robusta share × the world robusta price, plus its arabica share × the world arabica price). A realisation of 100% means the country is paid exactly the benchmark for its mix.

**Finding:** **Uganda realises about 85% of the reference for its mix**: more than Vietnam (82%) and every West and Central African robusta exporter (68–76%), but less than India (96%) and Indonesia (106%), whose exports include more washed and specialty coffee. Producers further above the reference tend to sell specialty grades, washed coffee or processed products; those below it sell lower grades or face high marketing costs. Unit values are averages across all grades and destinations, so they measure the overall price received, not quality directly.
"""),

('md', '---\n## 5. Stability and home consumption'),
('code', r"""
vol = 100 * np.log(prod.loc[2000:2025].replace(0, np.nan)).diff().std()
stab = pd.DataFrame({'group': peers['group'], 'typical year-to-year production swing (%)': vol.loc[peers.index],
                     'share consumed at home (%)': peers['consumed_at_home']})
stab.sort_values('typical year-to-year production swing (%)').round(1)
"""),
('md', r"""
**Finding:** Uganda's production swings by about 13% from one year to the next, in the middle of the pack: steadier than Brazil (frost and drought, about 20%) and far steadier than several West African producers (over 30%), but less steady than India or Ethiopia (6–9%).

Uganda consumes only about 4% of its coffee at home, among the lowest of all peers. Ethiopia (about 40%), Brazil (about 35%) and Indonesia (about 45%) have large home markets that absorb surpluses and support local roasting and value addition. For Uganda, a growing domestic market is an untapped buffer.
"""),

('md', '---\n## 6. The data gap: three sources, three numbers'),
('code', r"""
cd = load_exports_annual()
cd.index = [int(i[:4]) for i in cd.index]            # financial year starting July of that year
usda = exp_['Uganda']                                    # market year starting October of that year
tq = fao_t[(fao_t['Area'] == 'Uganda') & (fao_t['Element'] == 'Export quantity')]
fao_bags = pd.Series({y: tq[f'Y{y}'].iloc[0] * 1000 / BAG_KG for y in range(2010, 2025)})   # calendar year
gap = pd.DataFrame({'Coffee Department (Jul–Jun)': cd['total_bags'] / 1e6,
                    'USDA (Oct–Sep)': usda / 1000, 'FAOSTAT (calendar year)': fao_bags / 1e6}).loc[2010:2025]
gap['largest gap (%)'] = 100 * (gap.max(axis=1) / gap.min(axis=1) - 1)
gap.round(2)
"""),
('code', r"""
fig, ax = plt.subplots(figsize=(10, 3.8))
for c, col, ls in [('Coffee Department (Jul–Jun)', INK, '-'), ('USDA (Oct–Sep)', ROB, '--'), ('FAOSTAT (calendar year)', ARA, ':')]:
    ax.plot(gap.index, gap[c], color=col, lw=2.2, ls=ls, marker='o', ms=3, label=c)
ax.set_ylabel('Million 60-kg bags'); ax.set_title("Uganda's coffee exports, by source"); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
"""),
('md', r"""
**Finding:** USDA's figures for Uganda matched the Coffee Department's almost exactly until 2021, then diverged. **For 2024/25 the Coffee Department reports 7.75 million bags and USDA 6.35 million (22% less); for 2025/26, 8.37 against 6.70 million (25% less).** FAOSTAT counts calendar years, which splits harvests differently, so it can differ by up to 30% in a single year without disagreeing about the trend; its 2024 figure (6.4 million bags) sits close to USDA's.

Possible reasons include coffee from neighbouring countries (eastern DR Congo, South Sudan) being exported through Uganda, different treatment of stocks, and USDA's practice of building its estimates from production rather than customs records. This matters for any benchmark: on USDA figures, Uganda's growth since 2021 is much smaller than the national figures show. **This report uses USDA for cross-country comparisons, so that every country is measured the same way, and the Coffee Department's figures for Uganda-only analysis.**
"""),

('md', '---\n## Export'),
('code', r"""
from pathlib import Path
out = Path('../data/processed')
bench = peers[['set', 'group', 'Production', 'Exports', 'world_production_share', 'world_export_share', 'production_rank',
               'export_rank', 'robusta_share', 'consumed_at_home']].join(growth.drop(columns='group')).join(
               yields.drop(columns='group')).join(prices.drop(columns='group')).join(stab.drop(columns=['group', 'share consumed at home (%)']))
bench.round(3).to_csv(out / 'benchmark_peers.csv')
gap.round(4).to_csv(out / 'benchmark_uganda_source_gap.csv')
(prod.loc[1990:2025, peers.index] / 1000).round(4).to_csv(out / 'benchmark_production_series.csv')
print('Saved 3 tables to data/processed/')
"""),
('md', r"""
---
## Summary

- **Uganda is the world's 6th-largest coffee producer and exporter, and Africa's largest exporter**, with about 4% of world exports.
- **It is the fastest-growing of the ten largest producers**, at about 5% a year since 2006–10, while most West and Central African robusta producers have shrunk.
- **Its biggest gap is yield**: perhaps a fifth of Vietnam's per hectare. But Uganda's yield is also the least reliable number in the data, because its harvested area is imputed.
- **It is paid about 85% of the world reference for its mix**: more than Vietnam and the other African robusta exporters, less than India and Indonesia.
- **It drinks almost none of its own coffee** (about 4%), unlike Ethiopia, Brazil or Indonesia.
- **Its export figures differ by source by 22–25% for the last two years.** Cross-country comparisons here use USDA so that all countries are measured alike.

**Caveats:** FAOSTAT yields and areas are imputed for many African producers; export unit values average across grades; USDA figures are estimates built from production, not customs records.
"""),
]

if __name__ == '__main__':
    out = ROOT / 'notebooks'
    out.mkdir(exist_ok=True)
    notebook(NB1, out / '01_exports_prices_and_farmgate.ipynb')
    notebook(NB2, out / '02_climate_and_exports.ipynb')
    notebook(NB3, out / '03_global_benchmark.ipynb')
