import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df=load(); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); L24=window(mc,'2024.M08',HIST_END)
L12=window(mc,'2025.M08',HIST_END); P12=window(mc,'2024.M08','2025.M07')
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')

rows=[]
for k in A.index:
    v=A.loc[k,L24].fillna(0).values.astype(float)
    if v.sum()<1000: continue
    live=A.loc[k,hist].fillna(0)
    first=A.loc[k,hist].first_valid_index()
    age=len(hist)-hist.index(first) if first else 0
    nz=(v>0).mean()                                  # activity: share of months with a shipment
    mu=v.mean(); sd=v.std()
    cv=sd/mu if mu>0 else np.nan                     # volatility
    a12=A.loc[k,L12].fillna(0).sum(); ap12=A.loc[k,P12].fillna(0).sum()
    trend=(a12-ap12)/ap12 if ap12>0 else np.nan
    # year-over-year repeatability of the monthly shape
    y1=np.array([A.loc[k,f'2024.M{m:02d}'] if f'2024.M{m:02d}' in mc else np.nan for m in range(8,13)]+
                [A.loc[k,f'2025.M{m:02d}'] for m in range(1,8)],dtype=float)
    y2=np.array([A.loc[k,f'2025.M{m:02d}'] for m in range(8,13)]+
                [A.loc[k,f'2026.M{m:02d}'] for m in range(1,8)],dtype=float)
    y1=np.nan_to_num(y1); y2=np.nan_to_num(y2)
    rep=float(np.corrcoef(y1,y2)[0,1]) if y1.std()>0 and y2.std()>0 else np.nan
    # top-month concentration: does one month carry the line?
    conc=float(np.sort(v)[-3:].sum()/v.sum()) if v.sum()>0 else np.nan
    cuts=SC.loc[k,L12].fillna(0).sum() if k in SC.index else 0
    has_e=(E.loc[k,L12].fillna(0).sum()>0) if k in E.index else False
    rows.append(dict(House=k[0],Brand=k[1],PL=k[2],CFG=k[3],vol=a12,age=age,
                     active=nz,cv=cv,trend=trend,rep_yoy=rep,conc=conc,
                     cut_rate=cuts/(a12+cuts) if (a12+cuts)>0 else 0,epos=has_e))
R=pd.DataFrame(rows)
print(f"Lines profiled (>=1000 u in last 24 months): {len(R)}  covering {R.vol.sum():,.0f} u\n")

# ---------------- archetype rules ----------------
def arch(r):
    if r.age<=12:                                   return 'NEW / LAUNCH'
    if r.active<0.5:                                return 'INTERMITTENT'
    if r.cv>1.0:                                    return 'LUMPY / EVENT-DRIVEN'
    if r.trend is not None and r.trend<-0.35:       return 'DECLINING'
    if r.cv<=0.6 and (r.rep_yoy if r.rep_yoy==r.rep_yoy else 0)>0.3: return 'STABLE & REPEATABLE'
    return 'MODERATE'
R['archetype']=R.apply(arch,axis=1)
order=['STABLE & REPEATABLE','MODERATE','LUMPY / EVENT-DRIVEN','INTERMITTENT','DECLINING','NEW / LAUNCH']
print("="*95); print("ARCHETYPES — how forecastable each group is"); print("="*95)
print(f"{'archetype':24s} {'lines':>6} {'% vol':>7} {'CV':>6} {'active':>7} {'rep_yoy':>7} {'cut rate':>9} {'EPOS':>6}")
summ={}
for a in order:
    g=R[R.archetype==a]
    if not len(g): continue
    print(f"{a:24s} {len(g):>6} {g.vol.sum()/R.vol.sum():>6.1%} {g.cv.median():>6.2f} "
          f"{g.active.median():>6.0%} {g.rep_yoy.median():>7.2f} {g.cut_rate.median():>8.1%} {g.epos.mean():>5.0%}")
    summ[a]=dict(n=int(len(g)),vol=float(g.vol.sum()),vol_sh=float(g.vol.sum()/R.vol.sum()),
                 cv=float(g.cv.median()),active=float(g.active.median()),
                 repeat=float(g.rep_yoy.median()) if g.rep_yoy.notna().any() else None,
                 cut=float(g.cut_rate.median()),epos=float(g.epos.mean()))

# ---------------- predictability score ----------------
def score(r):
    s=0
    s+= 30 if r.cv<0.6 else 20 if r.cv<0.9 else 10 if r.cv<1.3 else 0      # volatility
    s+= 25 if r.active>0.9 else 15 if r.active>0.7 else 5 if r.active>0.5 else 0  # continuity
    rp=r.rep_yoy if r.rep_yoy==r.rep_yoy else 0
    s+= 25 if rp>0.5 else 15 if rp>0.25 else 5 if rp>0 else 0              # repeatability
    s+= 10 if r.age>=24 else 5 if r.age>=12 else 0                          # history depth
    s+= 10 if r.epos else 0                                                 # sell-out visibility
    return s
R['score']=R.apply(score,axis=1)
R['band']=pd.cut(R.score,[-1,39,59,79,100],labels=['LOW','FAIR','GOOD','HIGH'])
print("\n"+"="*95); print("FORECASTABILITY SCORE (0-100)"); print("="*95)
b=R.groupby('band',observed=True).agg(lines=('score','size'),vol=('vol','sum'),cv=('cv','median'),
                                      rep=('rep_yoy','median'),cut=('cut_rate','median'))
b['vol_sh']=b.vol/R.vol.sum()
print(b.to_string(formatters={'vol':'{:,.0f}'.format,'vol_sh':'{:.1%}'.format,'cv':'{:.2f}'.format,
                              'rep':'{:.2f}'.format,'cut':'{:.1%}'.format}))
print("\nBy house (median score):")
print(R.groupby('House').agg(lines=('score','size'),median_score=('score','median'),
      vol=('vol','sum'),cv=('cv','median')).sort_values('median_score',ascending=False)
      .to_string(formatters={'vol':'{:,.0f}'.format,'cv':'{:.2f}'.format}))
print("\nBy CFG (median score):")
print(R.groupby('CFG').agg(lines=('score','size'),median_score=('score','median'),cv=('cv','median'),
      active=('active','median'),cut=('cut_rate','median')).to_string(
      formatters={'cv':'{:.2f}'.format,'active':'{:.0%}'.format,'cut':'{:.1%}'.format}))

print("\n--- The 15 most forecastable lines (build the plan on these) ---")
print(R.nlargest(15,'score')[['House','PL','CFG','vol','score','cv','active','rep_yoy']].to_string(
      index=False,formatters={'vol':'{:,.0f}'.format,'cv':'{:.2f}'.format,'active':'{:.0%}'.format,'rep_yoy':'{:.2f}'.format}))
print("\n--- The 15 least forecastable HIGH-VOLUME lines (these need judgement, not the system) ---")
big=R[R.vol>R.vol.quantile(.7)]
print(big.nsmallest(15,'score')[['House','PL','CFG','vol','score','cv','active','rep_yoy','archetype']].to_string(
      index=False,formatters={'vol':'{:,.0f}'.format,'cv':'{:.2f}'.format,'active':'{:.0%}'.format,'rep_yoy':'{:.2f}'.format}))

R.to_csv('analysis/out/a6_archetypes.csv',index=False)
json.dump(dict(summary=summ,
  bands={str(k):dict(n=int(v['lines']),vol=float(v['vol']),sh=float(v['vol_sh'])) for k,v in b.iterrows()},
  house={k:float(v) for k,v in R.groupby('House').score.median().items()},
  cfg={k:float(v) for k,v in R.groupby('CFG').score.median().items()},
  n=len(R),vol=float(R.vol.sum())),
  open('analysis/out/a6.json','w'),indent=1,default=float)
