"""
Collect every number shown in reports/coffee_report.html and inject it into the page.

Model results come from the tables notebook 01 exports to data/processed/; chart series are
computed with the shared loaders in coffee.py, so the page always matches the notebook.

Usage (from anywhere, after running notebook 01):
    python scripts/build_report_data.py
"""
import json
import re
import numpy as np
import pandas as pd
from coffee import (ROOT, PROC, load_world, load_fx, load_cpi, load_farmgate, load_exports_monthly,
                    load_exports_annual, load_maize_kampala)

REPORT = ROOT / 'reports' / 'coffee_report.html'


def r4(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 4)


def main():
    world, fx, cpi = load_world(), load_fx(), load_cpi()
    farm, monthly, annual = load_farmgate(), load_exports_monthly(), load_exports_annual()

    ann = [{'fy': fy, 'total': r4(r['total_bags']), 'rob': r4(r['robusta_bags']), 'ara': r4(r['arabica_bags']),
            'usd_m': r4(r['total_usd_m'])} for fy, r in annual.iterrows()]

    e = monthly.join(world, rsuffix='_world')
    exp = [{'d': str(p), 'rob': r4(r['robusta_usd_kg']), 'rob_w': r4(r['robusta_usd_kg_world']),
            'ara': r4(r['arabica_usd_kg']), 'ara_w': r4(r['arabica_usd_kg_world'])} for p, r in e.iterrows()]
    ratio = e.assign(r=e['robusta_usd_kg'] / e['robusta_usd_kg_world'], a=e['arabica_usd_kg'] / e['arabica_usd_kg_world'])

    d = farm.join(world).join(fx)
    d['share'] = d['faq_ugx'] / (d['robusta_usd_kg'] * d['ugx_per_usd'])
    d['world_rob_ugx'] = d['robusta_usd_kg'] * d['ugx_per_usd']
    share_m = [{'d': str(p), 'v': r4(v)} for p, v in d['share'].items() if pd.notna(v)]
    share_y = pd.read_csv(PROC / 'farmer_share_by_year.csv', index_col=0)
    share_y = [{'y': int(y), 'v': r4(v)} for y, v in share_y['farmer_share_faq'].items() if pd.notna(v)]

    z = d.loc['2019-06':]
    boom = [{'d': str(p), 'world': r4(r['world_rob_ugx']), 'faq': r4(r['faq_ugx']), 'kib': r4(r['kiboko_ugx'])} for p, r in z.iterrows()]
    A, B = d.loc['2020'].mean(numeric_only=True), d.loc['2025'].mean(numeric_only=True)
    total = np.log(B['faq_ugx'] / A['faq_ugx'])
    decomp = {'faq_2020': r4(A['faq_ugx']), 'faq_2025': r4(B['faq_ugx']), 'multiple': r4(np.exp(total)),
              'world_pct': r4(100 * np.log(B['robusta_usd_kg'] / A['robusta_usd_kg']) / total),
              'fx_pct': r4(100 * np.log(B['ugx_per_usd'] / A['ugx_per_usd']) / total),
              'share_pct': r4(100 * np.log(B['share'] / A['share']) / total)}
    last = d['faq_ugx'].dropna().index[-1]
    peaks = {'faq_peak': r4(d['faq_ugx'].max()), 'faq_peak_d': str(d['faq_ugx'].idxmax()),
             'faq_last': r4(d.loc[last, 'faq_ugx']), 'faq_last_d': str(last),
             'world_peak': r4(world['robusta_usd_kg'].max()), 'world_peak_d': str(world['robusta_usd_kg'].idxmax()),
             'world_last': r4(world['robusta_usd_kg'].iloc[-1]), 'world_last_d': str(world.index[-1])}

    pt = pd.read_csv(PROC / 'price_passthrough.csv').round(4).to_dict('records')
    cal = pd.read_csv(PROC / 'export_calendar.csv', index_col=0)
    cal = {'months': cal.index.tolist(), 'rob': [r4(v) for v in cal['robusta']], 'ara': [r4(v) for v in cal['arabica']]}

    mz = load_maize_kampala()
    real = pd.DataFrame({'Robusta FAQ': farm['faq_ugx'], 'Robusta kiboko': farm['kiboko_ugx'],
                         'Arabica parchment': farm['parchment_ugx'], 'Maize, Kampala retail': mz}).div(cpi, axis=0)
    risk = []
    for c in real.columns:
        x = np.log(real[c])
        worst = x.diff(12)
        risk.append({'price': c, 'monthly': r4(100 * x.loc['2020-01':'2026-03'].diff().std()),
                     'year': r4(100 * x.loc['2020-01':'2026-03'].diff(12).std()),
                     'worst': r4(100 * (np.exp(worst.min()) - 1)), 'worst_d': str(worst.idxmin())})

    last_fy = annual.index[-1]
    data = {
        'annual': ann, 'exports_vs_world': exp,
        'ratio_by_year': {int(y): {'rob': r4(v['r']), 'ara': r4(v['a'])} for y, v in ratio.groupby(ratio.index.year)[['r', 'a']].mean().iterrows()},
        'share_monthly': share_m, 'share_yearly': share_y,
        'boom': boom, 'decomp': decomp, 'peaks': peaks,
        'passthrough': pt, 'calendar': cal, 'risk': risk,
        'kpi': {'last_fy': last_fy, 'last_bags': r4(annual.loc[last_fy, 'total_bags']),
                'record_usd_m': r4(annual['total_usd_m'].max()), 'record_usd_fy': annual['total_usd_m'].idxmax(),
                'bags_2015_16': r4(annual.loc['2015/16', 'total_bags']),
                'corrections': int(pd.read_csv(PROC / 'monthly_reports_extracted.csv')['notes'].notna().sum()),
                'reports': int(len(pd.read_csv(PROC / 'monthly_reports_extracted.csv')))},
    }
    (PROC / 'report_data.json').write_text(json.dumps(data, indent=1))
    s = REPORT.read_text()
    payload = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    s, n = re.subn(r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
                   lambda m: m.group(1) + payload + m.group(3), s, flags=re.S)
    if n != 1:
        raise SystemExit(f'expected one report-data block, found {n}')
    REPORT.write_text(s)
    print('updated', REPORT.relative_to(ROOT))


if __name__ == '__main__':
    main()
