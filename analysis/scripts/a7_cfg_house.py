import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df=load(); dfa=load(exclude_multiline=False); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); L12=window(mc,'2025.M08',HIST_END)
ehist=window(mc,'2024.M07',HIST_END); fwd=window(mc,FWD_START,FWD_END)
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')
out={}

print("="*90); print("CFG PROFILE: P_US_ULTA vs P_US_ALL_OTHERS"); print("="*90)
cfgstat={}
for g in ['P_US_ULTA','P_US_ALL_OTHERS']:
    a=A.xs(g,level='CFG'); e=E.xs(g,level='CFG') if g in E.index.get_level_values('CFG') else None
    s=SC.xs(g,level='CFG'); c=C.xs(g,level='CFG')
    v12=a[L12].sum().sum(); cuts=s[L12].sum().sum()
    lines=int((a[L12].sum(axis=1)>0).sum())
    cv=(a[L12].std(axis=1)/a[L12].mean(axis=1)).replace([np.inf],np.nan).median()
    act=(a[L12].fillna(0)>0).mean(axis=1).median()
    d={'lines':lines,'vol12':float(v12),'share':None,'cuts':float(cuts),
       'cutrate':float(cuts/(v12+cuts)),'cv':float(cv),'active':float(act),
       'fwd':float(c[fwd].sum().sum())}
    cfgstat[g]=d
tv=sum(v['vol12'] for v in cfgstat.values())
for g,d in cfgstat.items(): d['share']=d['vol12']/tv
for g,d in cfgstat.items():
    print(f"\n{g}")
    print(f"  active lines            {d['lines']}")
    print(f"  volume last 12m         {d['vol12']:>12,.0f} u  ({d['share']:.0%} of scope)")
    print(f"  forward book            {d['fwd']:>12,.0f} u")
    print(f"  demand lost to cuts     {d['cutrate']:>12.1%}  ({d['cuts']:,.0f} u)")
    print(f"  median line volatility  {d['cv']:>12.2f} CV")
    print(f"  median months active    {d['active']:>12.0%}")
out['cfg']=cfgstat

# EPOS quality by CFG
print("\nEPOS signal quality by CFG:")
eq={}
for g in ['P_US_ULTA','P_US_ALL_OTHERS']:
    a=A.xs(g,level='CFG'); e=E.xs(g,level='CFG')
    common=a.index.intersection(e.index)
    ta=a.loc[common,ehist].fillna(0).sum(axis=1); te=e.loc[common,ehist].fillna(0).sum(axis=1)
    liv=ta>2000
    covr=float((te[liv]/ta[liv]).median())
    withe=float((te[liv]>0).mean())
    # aggregate lag
    aa=a[ehist].sum(); ee=e[ehist].sum()
    best=max(((k,float(np.corrcoef(aa.values[:len(aa)-k] if k else aa.values,
              ee.values[k:] if k else ee.values)[0,1])) for k in range(0,5)),key=lambda t:t[1])
    eq[g]=dict(coverage=covr,pct_with_epos=withe,best_lag=best[0],r=best[1])
    print(f"  {g:18s} coverage {covr:.0%}   lines with EPOS {withe:.0%}   best lag {best[0]}m (r={best[1]:+.2f})")
out['epos_quality']=eq

print("\n"+"="*90); print("HOUSE PROFILES"); print("="*90)
hs={}
for h in sorted(set(A.index.get_level_values('House'))):
    a=A.xs(h,level='House'); c=C.xs(h,level='House') if h in C.index.get_level_values('House') else None
    s=SC.xs(h,level='House') if h in SC.index.get_level_values('House') else None
    e=E.xs(h,level='House') if h in E.index.get_level_values('House') else None
    v12=a[L12].sum().sum(); cuts=s[L12].sum().sum() if s is not None else 0
    idx,_=seasonal_index(a[hist].sum().to_dict(),[2024,2025])
    pk=sorted(idx.items(),key=lambda t:-t[1])[:3] if idx else []
    tr=(a[L12].sum().sum()-a[window(mc,'2024.M08','2025.M07')].sum().sum())/max(a[window(mc,'2024.M08','2025.M07')].sum().sum(),1)
    hs[h]=dict(lines=int(a.index.get_level_values('Product Line').nunique()),vol12=float(v12),
               cuts=float(cuts),cutrate=float(cuts/(v12+cuts)) if (v12+cuts)>0 else 0,
               fwd=float(c[fwd].sum().sum()) if c is not None else 0,trend=float(tr),
               peaks=[(MONTH_ABBR[m-1],round(v)) for m,v in pk],index=idx)
    print(f"\n{h}")
    print(f"  product lines {hs[h]['lines']:<4} volume L12M {v12:>11,.0f} u   YoY {tr:>+7.0%}   forward book {hs[h]['fwd']:>11,.0f} u")
    print(f"  demand lost to cuts {hs[h]['cutrate']:>6.1%}   peak months: " + ", ".join(f"{m} ({v})" for m,v in hs[h]['peaks']))
out['house']=hs

# ---- the excluded Multiline line, on its own ----
print("\n"+"="*90); print("GUCCI FRAGRANCE MULTILINE (00003484) — reported separately"); print("="*90)
Am=measure(dfa,'Actuals'); Cm=measure(dfa,'Consensus - Final'); Em=measure(dfa,'EPOS'); Sm=measure(dfa,'Supply Cuts')
msk=[k for k in Am.index if k[2]==MULTILINE]
ml_a=Am.loc[msk]; ml_c=Cm.loc[[k for k in Cm.index if k[2]==MULTILINE]]
ml_e=Em.loc[[k for k in Em.index if k[2]==MULTILINE]]
ml_s=Sm.loc[[k for k in Sm.index if k[2]==MULTILINE]]
scope_a=A[L12].sum().sum()
print(f"  volume last 12 closed months : {ml_a[L12].sum().sum():>12,.0f} u")
print(f"  = {ml_a[L12].sum().sum()/(ml_a[L12].sum().sum()+scope_a):.0%} of total scope volume")
print(f"  forward book                 : {ml_c[fwd].sum().sum():>12,.0f} u")
print(f"  EPOS last 12m                : {ml_e[L12].sum().sum():>12,.0f} u  (ratio to sell-in {ml_e[L12].sum().sum()/ml_a[L12].sum().sum():.3f})")
print(f"  supply cuts last 12m         : {ml_s[L12].sum().sum():>12,.0f} u")
cv=(ml_a[L12].std(axis=1)/ml_a[L12].mean(axis=1))
print(f"  volatility (CV) by CFG       : " + ", ".join(f"{k[3]} {v:.2f}" for k,v in cv.items()))
idxm,_=seasonal_index(ml_a[hist].sum().to_dict(),[2024,2025])
print("  seasonal index               : " + " ".join(f"{MONTH_ABBR[m-1]} {idxm[m]:.0f}" for m in range(1,13)))
ml=dict(vol12=float(ml_a[L12].sum().sum()),share=float(ml_a[L12].sum().sum()/(ml_a[L12].sum().sum()+scope_a)),
        fwd=float(ml_c[fwd].sum().sum()),epos=float(ml_e[L12].sum().sum()),
        cuts=float(ml_s[L12].sum().sum()),index=idxm,
        epos_ratio=float(ml_e[L12].sum().sum()/ml_a[L12].sum().sum()))
out['multiline']=ml
mmax=ml_a[hist].sum(); print(f"  biggest single month in history: {mmax.idxmax()} = {mmax.max():,.0f} u "
      f"({mmax.max()/mmax[mmax>0].median():.0f}x its own median month)")
ml['spike']=dict(month=str(mmax.idxmax()),units=float(mmax.max()),x=float(mmax.max()/mmax[mmax>0].median()))
json.dump(out,open('analysis/out/a7.json','w'),indent=1,default=float)
