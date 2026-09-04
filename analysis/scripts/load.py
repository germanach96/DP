"""Shared loader for the O9 scope extract.

Conventions agreed with the user:
  - History is overwritten in O9: for every closed month System FC = Consensus = Actuals.
    Therefore no lag-based accuracy (MAPE/BIAS) can be computed from this extract.
  - Closed history window ends 2026.M07 (2026.M08 still invoicing, 2026.M09 in flight).
  - Gucci Fragrance Multiline (00003484) is a catch-all line = 32% of volume; excluded
    from every aggregate and given its own section.
  - Values are units. EPOS covers only part of the retailer base, so it is used as an
    index/trend signal, never as an absolute level against sell-in.
"""
import pandas as pd, numpy as np, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
XLSX = ROOT / 'scope analysis.xlsx'

KEY = ['House', 'Brand', 'Product Line', 'CFG']
HIST_END   = '2026.M07'     # last fully closed month
HIST_START = '2023.M08'     # first month with actuals
FWD_START  = '2026.M08'     # forward book starts here
FWD_END    = '2029.M07'     # last month with a consensus
MULTILINE  = 'Gucci Fragrance Multiline (00003484)'

MEASURES = ['System FC - Final', 'Initiative Forecast', 'Prometheus Fcst Consensus',
            'Customer Fcst', 'EPOS', 'Reasonability Adjustment',
            'Total Demand Assumption', 'Consensus - Final', 'Actuals', 'Supply Cuts']

MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


def month_cols(df):
    return [c for c in df.columns if '.M' in str(c)]


def window(cols, start=None, end=None):
    return [c for c in cols if (start is None or c >= start) and (end is None or c <= end)]


def mnum(col):
    """'2025.M09' -> 9"""
    return int(col.split('.M')[1])


def yr(col):
    return col.split('.')[0]


def load(exclude_multiline=True):
    df = pd.read_excel(XLSX, sheet_name='SCOPE')
    df.columns = [str(c) for c in df.columns]
    if exclude_multiline:
        df = df[df['Product Line'] != MULTILINE].copy()
    return df.reset_index(drop=True)


def measure(df, name):
    """Wide frame indexed by KEY for one measure."""
    m = df[df['Data'] == name].set_index(KEY)[month_cols(df)]
    return m[~m.index.duplicated()]


def panel(df):
    """Long tidy panel: one row per key x month x measure."""
    mc = month_cols(df)
    d = df.melt(id_vars=KEY + ['Data'], value_vars=mc,
                var_name='month', value_name='v')
    d['year'] = d['month'].str.slice(0, 4).astype(int)
    d['m'] = d['month'].str.split('.M').str[1].astype(int)
    return d


def seasonal_index(series_by_month, years):
    """Given a dict month_col -> value, return a 12-slot index (mean=100)
    computed per calendar year first, then averaged, so a big year does not
    dominate the shape."""
    per_year = {}
    for y in years:
        vals = {mnum(c): v for c, v in series_by_month.items() if yr(c) == str(y)}
        if len(vals) < 12:
            continue
        tot = sum(vals.values())
        if tot <= 0:
            continue
        per_year[y] = {k: v / tot * 12 * 100 for k, v in vals.items()}
    if not per_year:
        return None, {}
    idx = {m: np.mean([per_year[y][m] for y in per_year]) for m in range(1, 13)}
    return idx, per_year
