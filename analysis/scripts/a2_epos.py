import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df = load(); mc = month_cols(df)
hist = window(mc, HIST_START, HIST_END)
ehist = window(mc, '2024.M07', HIST_END)          # EPOS available window
A = measure(df,'Actuals'); E = measure(df,'EPOS')
out={}

# ---------- coverage ratio at line level ----------
common = A.index.intersection(E.index)
aa = A.loc[common, ehist].fillna(0); ee = E.loc[common, ehist].fillna(0)
tot_a = aa.sum(axis=1); tot_e = ee.sum(axis=1)
live = (tot_a > 2000) & (tot_e > 0)
ratio = (tot_e[live]/tot_a[live])
print(f"Lines with both signals and meaningful volume: {live.sum()}")
print("EPOS / Sell-in coverage ratio (24M):")
print(ratio.describe(percentiles=[.1,.25,.5,.75,.9]).round(3).to_string())
out['coverage']= {k: float(v) for k,v in ratio.describe(percentiles=[.1,.25,.5,.75,.9]).items()}

by_cfg = ratio.groupby(level='CFG').median()
print("\nMedian coverage by CFG:"); print(by_cfg.round(3).to_string())
by_h = ratio.groupby(level='House').median()
print("\nMedian coverage by House:"); print(by_h.round(3).to_string())
out['cov_cfg']={k:float(v) for k,v in by_cfg.items()}; out['cov_house']={k:float(v) for k,v in by_h.items()}

# ---------- per-line lead/lag ----------
print("\n=== PER-LINE LEAD/LAG (sell-in leads EPOS by k months) ===")
res=[]
for k in common:
    a=A.loc[k,ehist].fillna(0).values.astype(float); e=E.loc[k,ehist].fillna(0).values.astype(float)
    if a.sum()<5000 or (e>0).sum()<12: continue
    best=None
    for lag in range(0,5):                    # sell-in at t-lag vs epos at t
        if lag==0: x,y=a,e
        else:      x,y=a[:-lag],e[lag:]
        if x.std()==0 or y.std()==0: continue
        r=float(np.corrcoef(x,y)[0,1])
        if best is None or r>best[1]: best=(lag,r)
    if best and best[1]>0.25: res.append((k,best[0],best[1],tot_a[k]))
lagdist=pd.Series([r[1] for r in res])
print(f"lines with a usable positive relationship: {len(res)} of {live.sum()}")
print("distribution of best lag (months sell-in leads sell-out):")
print(lagdist.value_counts().sort_index().to_string())
print(f"volume-weighted mean lag: {np.average([r[1] for r in res], weights=[r[3] for r in res]):.2f}")
out['lag_dist']={int(k):int(v) for k,v in lagdist.value_counts().sort_index().items()}
out['lag_wmean']=float(np.average([r[1] for r in res], weights=[r[3] for r in res]))

# ---------- divergence signal: sell-in vs sell-out momentum ----------
# last 6 closed months vs prior 6, both series, on lines with real EPOS
recent = window(mc,'2026.M02',HIST_END); prior = window(mc,'2025.M08','2026.M01')
rows=[]
for k in common:
    a_r=A.loc[k,recent].sum(); a_p=A.loc[k,prior].sum()
    e_r=E.loc[k,recent].sum(); e_p=E.loc[k,prior].sum()
    if a_p<3000 or e_p<300: continue
    ga=(a_r-a_p)/a_p; ge=(e_r-e_p)/e_p
    rows.append(dict(House=k[0],PL=k[2],CFG=k[3],sellin_g=ga,epos_g=ge,gap=ga-ge,vol=a_r))
D=pd.DataFrame(rows)
print(f"\n=== SELL-IN vs SELL-OUT MOMENTUM (last 6M vs prior 6M), n={len(D)} ===")
print(f"correlation of the two growth rates: r={D.sellin_g.corr(D.epos_g):+.3f}")
print(f"lines shipping FASTER than consumer offtake (gap>+25pp): {(D.gap>0.25).sum()}  -> {D[D.gap>0.25].vol.sum():,.0f} u")
print(f"lines shipping SLOWER than offtake (gap<-25pp):          {(D.gap<-0.25).sum()}  -> {D[D.gap<-0.25].vol.sum():,.0f} u")
print("\nTop 12 over-shipping vs consumer (inventory build risk):")
print(D.nlargest(12,'gap')[['House','PL','CFG','sellin_g','epos_g','gap','vol']].to_string(index=False,
      formatters={'sellin_g':'{:+.0%}'.format,'epos_g':'{:+.0%}'.format,'gap':'{:+.0%}'.format,'vol':'{:,.0f}'.format}))
print("\nTop 12 under-shipping vs consumer (upside / cut risk):")
print(D.nsmallest(12,'gap')[['House','PL','CFG','sellin_g','epos_g','gap','vol']].to_string(index=False,
      formatters={'sellin_g':'{:+.0%}'.format,'epos_g':'{:+.0%}'.format,'gap':'{:+.0%}'.format,'vol':'{:,.0f}'.format}))
D.to_csv('analysis/out/a2_momentum.csv',index=False)
out['mom_corr']=float(D.sellin_g.corr(D.epos_g))
out['over_n']=int((D.gap>0.25).sum()); out['under_n']=int((D.gap<-0.25).sum())
json.dump(out,open('analysis/out/a2_epos.json','w'),indent=1,default=float)
