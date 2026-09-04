import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df=load(); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); L6=window(mc,'2026.M02',HIST_END); L12=window(mc,'2025.M08',HIST_END)
P12=window(mc,'2024.M08','2025.M07')
fwd=window(mc,FWD_START,FWD_END); F12=window(mc,FWD_START,'2027.M07')
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')
keys=C.index.union(A.index)
rows=[]
for k in keys:
    a12 = A.loc[k,L12].sum() if k in A.index else 0
    a6  = A.loc[k,L6].sum()  if k in A.index else 0
    ap12= A.loc[k,P12].sum() if k in A.index else 0
    c12 = C.loc[k,F12].sum() if k in C.index else 0
    cf  = C.loc[k,fwd].sum() if k in C.index else 0
    cuts= SC.loc[k,L12].sum() if k in SC.index else 0
    e6  = E.loc[k,L6].sum()  if k in E.index else 0
    ep6 = E.loc[k,window(mc,'2025.M08','2026.M01')].sum() if k in E.index else 0
    # last month with a consensus
    lastc = C.loc[k,fwd].replace(0,np.nan).last_valid_index() if k in C.index else None
    rows.append(dict(House=k[0],Brand=k[1],PL=k[2],CFG=k[3],a12=a12,a6=a6,ap12=ap12,
                     c12=c12,cfwd=cf,cuts=cuts,e6=e6,ep6=ep6,last_cons=lastc))
W=pd.DataFrame(rows)
W['cut_rate']=W.cuts/(W.a12+W.cuts).replace(0,np.nan)
W['fwd_vs_run']=W.c12/W.a12.replace(0,np.nan)
W['epos_g']=(W.e6-W.ep6)/W.ep6.replace(0,np.nan)
W['sellin_g']=(W.a6-W.ap12/2)/(W.ap12/2).replace(0,np.nan)

flags={}
def rep(name,mask,cols,sortby,asc=False,n=12,desc=''):
    sub=W[mask].copy()
    print(f"\n### {name}  ({len(sub)} lines, {sub.a12.sum():,.0f} u last-12m) — {desc}")
    if len(sub): print(sub.sort_values(sortby,ascending=asc).head(n)[cols].to_string(index=False))
    flags[name]=dict(n=int(len(sub)),vol=float(sub.a12.sum()))
    sub.assign(flag=name).to_csv(f"analysis/out/wl_{name.split()[0].lower()}.csv",index=False)
    return sub

print("="*80); print("WATCHLIST — forward book health, cut on 2026.M07 closed history"); print("="*80)

f1=rep("LOST-FORECAST", (W.a12>3000)&(W.c12<W.a12*0.15), ['House','PL','CFG','a12','a6','c12','cfwd'],
   'a12',desc="selling but the next 12 months are essentially empty")
f2=rep("PHANTOM-FORECAST", (W.a12<200)&(W.c12>3000), ['House','PL','CFG','a12','a6','c12','cfwd'],
   'c12',desc="a real forward book on a line that has stopped selling")
f3=rep("SERVICE-LOSS", (W.cut_rate>0.20)&(W.cuts>5000), ['House','PL','CFG','a12','cuts','cut_rate','c12'],
   'cuts',desc="more than 20% of demand lost to supply cuts")
f4=rep("OVER-BOOKED", (W.a12>10000)&(W.fwd_vs_run>1.6), ['House','PL','CFG','a12','c12','fwd_vs_run'],
   'c12',desc="next 12 months booked >60% above the last 12 actuals")
f5=rep("UNDER-BOOKED", (W.a12>10000)&(W.fwd_vs_run<0.55), ['House','PL','CFG','a12','c12','fwd_vs_run'],
   'a12',desc="next 12 months booked >45% below the last 12 actuals")
f6=rep("CONSUMER-DECLINE", (W.a12>10000)&(W.epos_g<-0.25)&(W.fwd_vs_run>0.9),
   ['House','PL','CFG','a12','e6','ep6','epos_g','fwd_vs_run'],'a12',
   desc="consumer offtake down >25% but the forward book is held flat or up")
# 2027.M06 and 2029.M07 are global planning-horizon walls (90 and 58 lines end there),
# so a genuine cliff is a line that stops BEFORE the first wall.
f7=rep("HORIZON-CLIFF", (W.a12>10000)&(W.last_cons.notna())&(W.last_cons<'2027.M03'),
   ['House','PL','CFG','a12','last_cons','cfwd'],'a12',
   desc="an active line whose forecast stops well before the 2027.M06 planning wall")

W.to_csv('analysis/out/a5_watchlist_full.csv',index=False)
json.dump(flags,open('analysis/out/a5.json','w'),indent=1,default=float)
print("\n\nSUMMARY OF FLAGS")
for k,v in flags.items(): print(f"  {k:20s} {v['n']:>4} lines  {v['vol']:>12,.0f} u")
