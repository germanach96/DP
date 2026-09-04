import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df=load(); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); fwd=window(mc,FWD_START,FWD_END)
A=measure(df,'Actuals'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')
S=measure(df,'System FC - Final'); IFc=measure(df,'Initiative Forecast')
PR=measure(df,'Prometheus Fcst Consensus'); RA=measure(df,'Reasonability Adjustment')
TDA=measure(df,'Total Demand Assumption')
out={}

# ================= SUPPLY CUTS =================
print("="*70); print("SUPPLY CUTS")
print("="*70)
rows=[]
for y in ['2023','2024','2025','2026']:
    cols=[c for c in hist if c.startswith(y)]
    a=A[cols].sum().sum(); c=SC[cols].sum().sum()
    rows.append(dict(year=y,actuals=a,cuts=c,rate=c/(a+c)))
    print(f"{y}  actuals {a:>12,.0f}  cuts {c:>10,.0f}  lost-demand rate {c/(a+c):>6.1%}")
out['cuts_year']=rows

print("\nCut rate by calendar month (2024-2026, demand lost = cuts/(actuals+cuts)):")
cm={}
for m in range(1,13):
    cols=[c for c in hist if mnum(c)==m and c>='2024.M01']
    a=A[cols].sum().sum(); c=SC[cols].sum().sum()
    cm[m]=float(c/(a+c)) if (a+c)>0 else 0
    print(f"  {MONTH_ABBR[m-1]}: {cm[m]:>6.1%}   (cuts {c:>9,.0f})")
out['cuts_month']=cm

print("\nCut rate by house (2025-2026):")
cols=[c for c in hist if c>='2025.M01']
ch={}
for h in sorted(set(A.index.get_level_values('House'))):
    a=A.xs(h,level='House')[cols].sum().sum(); c=SC.xs(h,level='House')[cols].sum().sum() if h in SC.index.get_level_values('House') else 0
    ch[h]=float(c/(a+c)) if (a+c)>0 else 0
    print(f"  {h:26s} {ch[h]:>6.1%}  (cuts {c:>9,.0f} of demand {a+c:>11,.0f})")
out['cuts_house']=ch

print("\nCut rate by CFG (2025-2026):")
cc={}
for g in ['P_US_ULTA','P_US_ALL_OTHERS']:
    a=A.xs(g,level='CFG')[cols].sum().sum(); c=SC.xs(g,level='CFG')[cols].sum().sum()
    cc[g]=float(c/(a+c)); print(f"  {g:20s} {cc[g]:>6.1%}")
out['cuts_cfg']=cc

# chronic cut lines
cl=[]
for k in SC.index:
    c=SC.loc[k,cols].fillna(0); a=A.loc[k,cols].fillna(0) if k in A.index else c*0
    if c.sum()<2000: continue
    cl.append(dict(House=k[0],PL=k[2],CFG=k[3],cuts=float(c.sum()),actuals=float(a.sum()),
                   rate=float(c.sum()/(c.sum()+a.sum())),months=int((c>0).sum())))
CL=pd.DataFrame(cl).sort_values('cuts',ascending=False)
print(f"\nTop 15 lines by lost demand (2025-2026), total lost {CL.cuts.sum():,.0f} u:")
print(CL.head(15).to_string(index=False,formatters={'cuts':'{:,.0f}'.format,'actuals':'{:,.0f}'.format,'rate':'{:.1%}'.format}))
CL.to_csv('analysis/out/a4_cutlines.csv',index=False)

# cuts with zero consensus = demand we never planned
z=0; zc=0
for k in SC.index:
    if k not in C.index: continue
    c=SC.loc[k,cols].fillna(0); cons=C.loc[k,cols].fillna(0)
    m=(c>0)&(cons==0)
    z+=int(m.sum()); zc+=float(c[m].sum())
print(f"\nMonths with supply cuts but ZERO consensus: {z} line-months, {zc:,.0f} units of demand we never forecast")
out['cuts_nofcst']=dict(n=z,units=zc)

# ================= FORECAST LAYERS (forward book) =================
print("\n"+"="*70); print("FORWARD BOOK COMPOSITION (2026.M08 -> 2029.M07)"); print("="*70)
lay={'System FC - Final':S,'Initiative Forecast':IFc,'Prometheus Fcst Consensus':PR,
     'Reasonability Adjustment':RA,'Total Demand Assumption':TDA}
# Restrict every layer to the cells where a consensus actually exists, otherwise
# the layer sums and the consensus are taken over different cell sets and the
# residual is meaningless.
CM=C[fwd].notna()
tot_c=C[fwd].where(CM).sum().sum()
print(f"Consensus - Final forward book: {tot_c:,.0f} u\n")
comp={}; ssum=0.0
for n,M in lay.items():
    v=M.reindex(C.index)[fwd].where(CM).sum().sum(); comp[n]=float(v); ssum+=v
    print(f"  {n:28s} {v:>14,.0f}  ({v/tot_c:>+7.1%} of consensus)")
comp['__residual__']=float(tot_c-ssum)
print(f"  {'residual (no visible layer)':28s} {tot_c-ssum:>14,.0f}  ({(tot_c-ssum)/tot_c:>+7.1%} of consensus)")
print(f"  {'Customer Fcst':28s} {0:>14,.0f}  (measure is empty in the whole extract)")
out['fwd_comp']=comp; out['fwd_total']=float(tot_c)

print("\nManual-layer direction (how the team overrides the system):")
for n,M in [('Reasonability Adjustment',RA),('Total Demand Assumption',TDA)]:
    v=M[mc].stack().dropna()
    print(f"  {n}: n={len(v)}  negative {(v<0).mean():.0%}  positive {(v>0).mean():.0%}  "
          f"net {v.sum():>+12,.0f}  median {v.median():>+8,.0f}")
    out[f'dir_{n[:3]}']=dict(n=int(len(v)),neg=float((v<0).mean()),net=float(v.sum()),med=float(v.median()))

# Prometheus / TDA offsetting
off=0; offv=0
pi=PR.index.intersection(TDA.index)
for k in pi:
    p=PR.loc[k,mc].fillna(0); t=TDA.loc[k,mc].fillna(0)
    m=(p>1000)&(t<-1000)
    off+=int(m.sum()); offv+=float(p[m].sum())
print(f"\nPrometheus/TDA offset pattern: {off} line-months where Prometheus>0 and TDA<0 ({offv:,.0f} u gross loaded)")
out['offset']=dict(n=off,units=offv)

# forward book by year
print("\nForward consensus by year vs. the run rate it implies:")
run=A[window(mc,'2025.M08',HIST_END)].sum().sum()  # last 12 closed months
print(f"  last 12 closed months actuals: {run:,.0f} u")
fy={}
for y in ['2026','2027','2028','2029']:
    cols=[c for c in fwd if c.startswith(y)]
    v=C[cols].sum().sum(); fy[y]=dict(units=float(v),months=len(cols))
    print(f"  {y}: {v:>12,.0f} u over {len(cols):>2} months  = {v/len(cols):>10,.0f}/mo  ({v/len(cols)/(run/12):.0%} of current run rate)")
out['fwd_year']=fy
json.dump(out,open('analysis/out/a4.json','w'),indent=1,default=float)
