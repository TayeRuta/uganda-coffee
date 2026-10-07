"""
Extract monthly coffee exports and farm-gate prices from the Coffee Department's
monthly report PDFs (MAAIF, formerly UCDA), January 2020 onwards.

Usage (from anywhere, after scripts/fetch_data.py has downloaded the PDFs):
    python scripts/extract_monthly_reports.py

Output: data/processed/monthly_reports_extracted.csv, one row per month:
    month, total_bags, total_usd_m, robusta_bags, robusta_usd_m, arabica_bags, arabica_usd_m,
    kiboko_ugx, faq_ugx, parchment_ugx, drugar_ugx, source_file

Every figure is read from the report's own text. The first pages are laid out in two
columns, so words are grouped by column before matching, to stop the columns interleaving.
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / 'data' / 'raw' / 'monthly_reports'
OUT = ROOT / 'data' / 'processed' / 'monthly_reports_extracted.csv'

MONTHS = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST',
          'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
NUM = r'([\d][\d,\.]*)'


def column_text(page):
    """Text of a page, read column by column (left half, then right half)."""
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    mid = page.width / 2
    cols = []
    for side in (lambda w: w['x1'] <= mid + 5, lambda w: w['x0'] >= mid - 5):
        ws = sorted([w for w in words if side(w)], key=lambda w: (round(w['top'] / 3), w['x0']))
        cols.append(' '.join(w['text'] for w in ws))
    return '\n'.join(cols)


def squash(t):
    """Normalise spacing so phrases match whether or not the PDF kept spaces between words.
    Adjacent numbers keep a '|' between them so they can't merge into one."""
    t = re.sub(r'(?<=\d)\s+(?=\d)', '|', t)
    return re.sub(r'\s+', '', t).lower()


def num(s):
    try:
        return float(s.replace(',', '').rstrip('.')) if s else None
    except ValueError:
        return None


def find(pattern, text):
    m = re.search(pattern, text)
    return m.groups() if m else None


def parse(path):
    with pdfplumber.open(path) as pdf:
        pages = [column_text(p) for p in pdf.pages[:3]]
        header = pdf.pages[0].extract_text() or ''
        # The grade table (usually page 2) states each type's total; it is the primary source
        tables = squash(' '.join((p.extract_text() or '') for p in pdf.pages[:4]))
    # Match the month by its first three letters: one report's header reads "NOVEBER 2023"
    m = re.search(r'REPORT\s*[-–]?\s*([A-Z]{3,10})\s*,?\s*(\d{4})', header.upper())
    abbr = [x[:3] for x in MONTHS]
    month = f"{m.group(2)}-{abbr.index(m.group(1)[:3]) + 1:02d}" if m and m.group(1)[:3] in abbr else None

    s = squash(' '.join(pages))
    row = {'month': month, 'source_file': path.name}

    # Farm-gate prices: read each grade separately, within the sentence that starts "farm-gate prices"
    i = s.find('farm-gateprices')
    if i >= 0:
        fs = s[i:i + 400]
        for col, pat in [('kiboko_ugx', r'kibokoaveragedugx' + NUM), ('faq_ugx', r'faqugx' + NUM),
                         ('parchment_ugx', r'parchmentugx' + NUM), ('drugar_ugx', r'drugar(?:ugx)?' + NUM)]:
            g = find(pat, fs)
            if g:
                row[col] = num(g[0])

    # Total exports: "Coffee exports in <Month> <Year> amounted to N 60-kilo bags worth US$ X million".
    # Variants: "469,951-kilo bags" (2020, the 60 dropped) and "N bags worth" (2025 onwards).
    head = r'coffeeexportsin[a-z]+\d{4},?(?:amounted|totaled|totalled)(?:to)?'
    for pat in [head + NUM + r'\|?60-?kilo(?:gram)?bags?,?worthus\$' + NUM + r'(million|billion)',
                head + NUM + r'(?:-kilo)?bags?,?worthus\$' + NUM + r'(million|billion)']:
        ex = find(pat, s)
        if ex:
            row.update(total_bags=num(ex[0]), total_usd_m=num(ex[1]) * (1000 if ex[2] == 'billion' else 1))
            break

    # Robusta and arabica: "comprised N bags of Robusta valued at US$ X million and N bags of Arabica valued at US$ Y million",
    # or in 2020 "comprised N bags (US$ X million) of Robusta and N bags (US$ Y million) of Arabica"
    old = find(r'comprised' + NUM + r'bags\(us\$' + NUM + r'million\)ofrobustaand' + NUM + r'bags\(us\$' + NUM + r'million\)ofarabica', s)
    if old:
        row.update(robusta_bags=num(old[0]), robusta_usd_m=num(old[1]), arabica_bags=num(old[2]), arabica_usd_m=num(old[3]))
    else:
        rb = find(r'comprised(?:of)?' + NUM + r',?bagsofrobusta(?:valuedat|worth)(?:us\$)?(?:ugx)?' + NUM + r'million', s)
        if rb:
            row.update(robusta_bags=num(rb[0]), robusta_usd_m=num(rb[1]))
        else:
            rb = find(r'comprised(?:of)?' + NUM + r',?bagsofrobusta', s)
            if rb:
                row.update(robusta_bags=num(rb[0]))
        ar = find(r'robusta.{0,80}?and' + NUM + r',?bagsofarabica(?:valuedat|worth)(?:us\$)?' + NUM + r'million', s)
        if ar:
            row.update(arabica_bags=num(ar[0]), arabica_usd_m=num(ar[1]))
    for typ in ['robusta', 'arabica']:
        g = find(r'total' + typ + NUM, tables)
        if g and num(g[0]) and num(g[0]) > 1000:
            row[f'table_{typ}_bags'] = num(g[0])
    return row


def note(df, i, text):
    df.at[i, 'notes'] = (df.at[i, 'notes'] + '; ' if df.at[i, 'notes'] else '') + text


# Corrections that a general rule can't make safely, each checked by reading the report.
MANUAL = {
    '2020-11': ({'kiboko_ugx': 2000.0, 'faq_ugx': 3900.0},
                'farm-gate sentence prints the FAQ price (3,900) beside Kiboko (2,000); assigned by hand'),
    '2025-06': ({'robusta_usd_m': 248.57, 'arabica_bags': 107006.0, 'arabica_usd_m': 41.03},
                'robusta value (248.57) printed beside the arabica bag count; assigned by hand'),
}


def unit_value(usd_m, bags):
    return usd_m * 1e6 / (bags * 60) if pd.notna(usd_m) and pd.notna(bags) and bags > 0 else np.nan


def repair(df):
    """Fix typing slips in the reports and make totals consistent. Every change is noted."""
    df = df.sort_values('month').reset_index(drop=True)
    for i, r in df.iterrows():
        # Thousands written with a full stop: 3.75 for 3,750 (prices) or 64.532 for 64,532 (bags)
        for c in ['kiboko_ugx', 'faq_ugx', 'parchment_ugx', 'drugar_ugx']:
            if pd.notna(r[c]) and r[c] < 100:
                df.at[i, c] = r[c] * 1000
                note(df, i, f'{c} read as {r[c]:g}, scaled to {r[c] * 1000:g}')
        for c in ['total_bags', 'robusta_bags', 'arabica_bags']:
            if pd.notna(r[c]) and r[c] < 1000:
                df.at[i, c] = r[c] * 1000
                note(df, i, f'{c} read as {r[c]:g}, scaled to {r[c] * 1000:g}')
        if r['month'] in MANUAL:
            vals, why = MANUAL[r['month']]
            for c, v in vals.items():
                df.at[i, c] = v
            note(df, i, why)

    # When the summary sentence doesn't add up to the stated total, use the grade table's figure for a
    # type if it makes the month add up. (Only then: some reports also print last month's table.)
    for i, r in df.iterrows():
        T, R, A = r['total_bags'], r['robusta_bags'], r['arabica_bags']
        if not (pd.notna(T) and pd.notna(R) and pd.notna(A)) or abs(R + A - T) <= 0.01 * T:
            continue
        for typ, other in [('robusta', A), ('arabica', R)]:
            tb = r.get(f'table_{typ}_bags')
            if pd.notna(tb) and abs(tb + other - T) <= 0.01 * T:
                note(df, i, f'{typ} bags {r[typ + "_bags"]:g} in the summary text differ from the grade table; table value {tb:g} used')
                df.at[i, f'{typ}_bags'] = tb
                break

    # A component copied unchanged from the previous month (seen once, July 2021)
    for i in range(1, len(df)):
        for t in ['robusta', 'arabica']:
            same = all(df.at[i, f'{t}_{k}'] == df.at[i - 1, f'{t}_{k}'] for k in ['bags', 'usd_m'])
            if same and pd.notna(df.at[i, f'{t}_bags']) and pd.notna(df.at[i, 'total_bags']):
                other = 'arabica' if t == 'robusta' else 'robusta'
                for k, tot in [('bags', 'total_bags'), ('usd_m', 'total_usd_m')]:
                    df.at[i, f'{t}_{k}'] = df.at[i, tot] - df.at[i, f'{other}_{k}']
                note(df, i, f'{t} figures repeated the previous month; set to total minus {other}')

    # Typical price per kg for each type, from the months around each one, to judge which figure is wrong
    uv = {t: df.apply(lambda r: unit_value(r[f'{t}_usd_m'], r[f'{t}_bags']), axis=1) for t in ['robusta', 'arabica']}
    typical = {t: uv[t].rolling(7, center=True, min_periods=3).median() for t in uv}

    for i, r in df.iterrows():
        for kind, t, rb, ar in [('bags', 'total_bags', 'robusta_bags', 'arabica_bags'),
                                ('usd_m', 'total_usd_m', 'robusta_usd_m', 'arabica_usd_m')]:
            T, R, A = df.at[i, t], df.at[i, rb], df.at[i, ar]
            if pd.isna(T) and pd.notna(R) and pd.notna(A):
                df.at[i, t] = R + A
                continue
            if pd.notna(T) and pd.notna(R) and pd.notna(A) and abs(R + A - T) > 0.01 * T:
                # Which figure is out of line? Check each type's price per kg against nearby months.
                off = {}
                for typ, col in [('robusta', rb), ('arabica', ar)]:
                    cur = uv[typ].iat[i]
                    off[typ] = abs(cur / typical[typ].iat[i] - 1) if pd.notna(cur) and pd.notna(typical[typ].iat[i]) else 0
                bad = max(off, key=off.get)
                if off[bad] > 0.3:
                    col, other = (rb, ar) if bad == 'robusta' else (ar, rb)
                    new = T - df.at[i, other]
                    note(df, i, f'{bad} {kind} {df.at[i, col]:g} out of line with nearby prices; set to total minus the other type ({new:g})')
                    df.at[i, col] = new
                else:
                    note(df, i, f'stated total {kind} {T:g} did not equal robusta + arabica; total set to their sum ({R + A:g})')
                    df.at[i, t] = R + A
            if pd.notna(T) and pd.isna(R) and pd.notna(A):
                df.at[i, rb] = T - A
                note(df, i, f'robusta {kind} derived as total minus arabica')
            if pd.notna(T) and pd.notna(R) and pd.isna(A):
                df.at[i, ar] = T - R
                note(df, i, f'arabica {kind} derived as total minus robusta')
    return df


def main():
    rows = [parse(p) for p in sorted(PDF_DIR.glob('*.pdf'))]
    df = pd.DataFrame(rows)
    df['notes'] = ''
    # Some months were uploaded twice; keep the version with the most fields filled
    df['filled'] = df.notna().sum(axis=1)
    df = df.sort_values(['month', 'filled'], ascending=[True, False]).drop_duplicates('month').drop(columns='filled')
    df = repair(df)
    cols = ['month', 'total_bags', 'total_usd_m', 'robusta_bags', 'robusta_usd_m', 'arabica_bags', 'arabica_usd_m',
            'kiboko_ugx', 'faq_ugx', 'parchment_ugx', 'drugar_ugx', 'notes', 'source_file']
    df = df.reindex(columns=cols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f'{len(df)} months, {df["month"].min()} to {df["month"].max()}')
    print('missing values per column:')
    print(df.drop(columns='source_file').isna().sum().to_string())


if __name__ == '__main__':
    main()
