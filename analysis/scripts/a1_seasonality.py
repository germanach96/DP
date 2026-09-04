import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df = load()
mc = month_cols(df)
hist = window(mc, HIST_START, HIST_END)
A = measure(df,'Actuals'); E = measure(df,'EPOS'); SC = measure(df,'Supply Cuts')

out = {}

# ---- 1. Total sell-in seasonality (full calendar years only: 2024, 2025) ----
tot_a = A[hist].sum()
tot_e = E[hist].sum()
tot_c = SC[hist].sum()

idx_a, py_a = seasonal_index(tot_a.to_dict(), [2024,2025])
idx_e, py_e = seasonal_index(tot_e.to_dict(), [2025])   # EPOS only full in 2025
print("SELL-IN seasonal index (mean=100), avg of 2024+2025:")
for m in range(1,13):
    yrs = "  ".join(f"{py_a[y][m]:6.0f}" for y in sorted(py_a))
    print(f"  {MONTH_ABBR[m-1]}  idx={idx_a[m]:6.1f}   per-year: {yrs}")
out['sellin_index'] = idx_a
out['sellin_by_year'] = {str(k):v for k,v in py_a.items()}

print("\nEPOS (sell-out) seasonal index 2025:")
for m in range(1,13):
    print(f"  {MONTH_ABBR[m-1]}  idx={idx_e[m]:6.1f}")
out['epos_index'] = idx_e

# EPOS 2024 partial (Jul-Dec) + 2026 (Jan-Jul) -> stitch a 12m view Jul25-Jun26 too
e_ser = tot_e[tot_e>0]
print("\nEPOS raw monthly totals:")
for c in e_ser.index: print(f"   {c} {e_ser[c]:12,.0f}")

# ---- 2. Lag: cross-correlation between EPOS and sell-in ----
common = [c for c in hist if tot_e[c]>0]
a_ser = tot_a[common]; ee = tot_e[common]
print("\nCross-correlation EPOS(t) vs Sell-in(t+k)  [positive k = sell-in LEADS epos]")
lags={}
for k in range(-4,5):
    x=[];y=[]
    for i,c in enumerate(common):
        j=i+k
        if 0<=j<len(common):
            x.append(ee.iloc[i]); y.append(a_ser.iloc[j])
    if len(x)>8:
        r=np.corrcoef(x,y)[0,1]; lags[k]=round(float(r),3)
        print(f"   sell-in shifted {k:+d} : r={r:+.3f}")
out['lag_corr']=lags

# ---- 3. Same by house ----
print("\n=== SEASONAL INDEX BY HOUSE (sell-in, 2024+2025) ===")
house_idx={}
for h,g in A.groupby(level='House'):
    s=g[hist].sum()
    i,_=seasonal_index(s.to_dict(),[2024,2025])
    if i:
        house_idx[h]=i
        print(f"{h:26s} " + " ".join(f"{i[m]:5.0f}" for m in range(1,13)))
print(f"{'':26s} " + " ".join(f"{MONTH_ABBR[m-1]:>5s}" for m in range(1,13)))
out['house_index']=house_idx

# ---- 4. By CFG ----
print("\n=== SEASONAL INDEX BY CFG ===")
cfg_idx={}
for c,g in A.groupby(level='CFG'):
    s=g[hist].sum(); i,_=seasonal_index(s.to_dict(),[2024,2025])
    cfg_idx[c]=i
    print(f"{c:20s} " + " ".join(f"{i[m]:5.0f}" for m in range(1,13)))
cfg_epos={}
for c,g in E.groupby(level='CFG'):
    s=g[hist].sum(); i,_=seasonal_index(s.to_dict(),[2025])
    if i: cfg_epos[c]=i; print(f"{c:20s} EPOS " + " ".join(f"{i[m]:5.0f}" for m in range(1,13)))
out['cfg_index']=cfg_idx; out['cfg_epos_index']=cfg_epos

# ---- 5. Consistency: how reliable is each month's peak? ----
print("\n=== MONTH CONSISTENCY (share of product lines whose month is above their own median) ===")
pl = A.groupby(level=['House','Product Line'])[hist].sum()
cons={}
for m in range(1,13):
    cols=[c for c in hist if mnum(c)==m and yr(c) in ('2024','2025')]
    if not cols: continue
    sub=pl[cols]
    med=pl.median(axis=1)
    frac=((sub.T>med).T).values.mean()
    cons[m]=round(float(frac),3)
    print(f"  {MONTH_ABBR[m-1]}: {frac:.1%} of line-months above line median")
out['month_consistency']=cons

json.dump(out, open('analysis/out/a1_seasonality.json','w'), indent=1, default=float)
