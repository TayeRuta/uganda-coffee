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

if __name__ == '__main__':
    out = ROOT / 'notebooks'
    out.mkdir(exist_ok=True)
    notebook(NB1, out / '01_exports_prices_and_farmgate.ipynb')
