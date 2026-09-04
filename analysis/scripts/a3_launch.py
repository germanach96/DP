import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

df=load(); mc=month_cols(df); hist=window(mc,HIST_START,HIST_END)
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts')
out={}

launches=[]
for k,row in A[hist].iterrows():
    fv=row.first_valid_index()
    if fv is None or fv<'2023.M09': continue
    tail=hist[hist.index(fv):]
    if len(tail)<6: continue
    launches.append((k,fv,tail))
print(f"Genuine launches (first actual >= 2023.M09, >=6 months observed): {len(launches)}")
out['n_launches']=len(launches)

# ---- POOLED curve: sum every launch aligned at month 0 (robust to small lines) ----
H=18
pool=np.zeros(H); pool_n=np.zeros(H); pool_e=np.zeros(H); pool_en=np.zeros(H); pool_c=np.zeros(H)
for k,fv,tail in launches:
    v=A.loc[k,tail].fillna(0).values.astype(float)
    c=SC.loc[k,tail].fillna(0).values.astype(float) if k in SC.index else np.zeros(len(v))
    for i in range(min(H,len(v))):
        pool[i]+=v[i]; pool_n[i]+=1; pool_c[i]+=c[i]
    if fv>='2024.M08' and k in E.index:
        e=E.loc[k,tail].fillna(0).values.astype(float)
        for i in range(min(H,len(e))): pool_e[i]+=e[i]; pool_en[i]+=1
avg=pool/np.maximum(pool_n,1)
base=avg[:12].mean()
print("\n=== POOLED LAUNCH CURVE (average sell-in per launch, per relative month) ===")
print(f"{'relM':>5} {'n':>4} {'avg units':>11} {'idx (M0-11 avg=100)':>20} {'cum % of Y1':>12}")
cum=np.cumsum(avg[:12])/avg[:12].sum()*100
curve={}
for i in range(H):
    if pool_n[i]<10: break
    cs=f"{cum[i]:.0f}%" if i<12 else ""
    print(f"{i:>5} {int(pool_n[i]):>4} {avg[i]:>11,.0f} {avg[i]/base*100:>20.0f} {cs:>12}")
    curve[i]=dict(n=int(pool_n[i]),avg=float(avg[i]),idx=float(avg[i]/base*100),
                  cum=float(cum[i]) if i<12 else None)
out['pooled_curve']=curve
print(f"\nMonth 0 is {avg[0]/base:.2f}x the average month of year 1")
print(f"Month 0 alone = {cum[0]:.0f}% of year-1 volume; months 0-2 = {cum[2]:.0f}%; months 0-5 = {cum[5]:.0f}%")
out['m0_multiple']=float(avg[0]/base); out['cum_y1']={i:float(cum[i]) for i in range(12)}

# steady state: avg of relative months 6-11 vs month 0
ss=avg[6:12].mean()
print(f"Steady state (avg rel. months 6-11) = {ss:,.0f} u = {ss/avg[0]:.0%} of the launch month")
out['steady_ratio']=float(ss/avg[0])

# ---- per-line robust stats ----
sh3=[];sh1=[];pk=[];second=[]
for k,fv,tail in launches:
    v=A.loc[k,tail].fillna(0).values.astype(float)
    if len(v)<12 or v[:12].sum()<=0: continue
    sh1.append(v[0]/v[:12].sum()); sh3.append(v[:3].sum()/v[:12].sum())
    pk.append(int(np.argmax(v[:12])))
    nz=np.nonzero(v[1:])[0]
    second.append(int(nz[0])+1 if len(nz) else 99)
sh1=pd.Series(sh1);sh3=pd.Series(sh3);pk=pd.Series(pk);second=pd.Series(second)
print(f"\nPer-line: month-0 share of year-1 volume  median={sh1.median():.0%} (p25 {sh1.quantile(.25):.0%} / p75 {sh1.quantile(.75):.0%})")
print(f"Per-line: months 0-2 share of year-1 volume median={sh3.median():.0%} (p25 {sh3.quantile(.25):.0%} / p75 {sh3.quantile(.75):.0%})")
print(f"\nPeak month within year 1: M0={  (pk==0).mean():.0%}  M0-M1={(pk<=1).mean():.0%}  M0-M2={(pk<=2).mean():.0%}")
print(f"Months until the SECOND shipment: median={second[second<99].median():.0f}  ({(second==1).mean():.0%} reorder immediately in M1)")
out['sh1']=dict(med=float(sh1.median()),p25=float(sh1.quantile(.25)),p75=float(sh1.quantile(.75)))
out['sh3']=dict(med=float(sh3.median()),p25=float(sh3.quantile(.25)),p75=float(sh3.quantile(.75)))
out['peak']={'M0':float((pk==0).mean()),'M0_M1':float((pk<=1).mean()),'M0_M2':float((pk<=2).mean())}
out['peak_dist']={int(k):float(v) for k,v in (pk.value_counts(normalize=True).sort_index()).items()}

# ---- EPOS ramp, pooled ----
avg_e=pool_e/np.maximum(pool_en,1)
print("\n=== POOLED EPOS RAMP on launches (avg per launch) ===")
ramp={}
for i in range(H):
    if pool_en[i]<8: break
    ratio=avg_e[i]/avg[i] if avg[i]>0 else np.nan
    print(f"  relM{i:<2} n={int(pool_en[i]):<3} EPOS {avg_e[i]:>9,.0f}   EPOS/sell-in {ratio:>6.2f}")
    ramp[i]=dict(n=int(pool_en[i]),epos=float(avg_e[i]),ratio=float(ratio) if avg[i]>0 else None)
out['epos_ramp']=ramp
pe=avg_e[:12]; print(f"EPOS peaks at relative month {int(np.argmax(pe))}, sell-in peaks at relative month {int(np.argmax(avg[:12]))}")
out['epos_peak_relm']=int(np.argmax(pe))

# ---- cuts during launch ----
avg_c=pool_c/np.maximum(pool_n,1)
print("\nSupply cuts during the launch window (avg per launch, cut rate = cuts/(actuals+cuts)):")
cuts={}
for i in range(min(12,H)):
    if pool_n[i]<10: break
    cr=avg_c[i]/(avg[i]+avg_c[i]) if (avg[i]+avg_c[i])>0 else 0
    print(f"  relM{i:<2} cuts {avg_c[i]:>8,.0f}  cut rate {cr:>6.1%}")
    cuts[i]=dict(cuts=float(avg_c[i]),rate=float(cr))
out['launch_cuts']=cuts

lm=pd.Series([mnum(fv) for k,fv,tail in launches])
out['launch_months']={MONTH_ABBR[k-1]:int(v) for k,v in lm.value_counts().sort_index().items()}
print("\nLaunch calendar month:", {MONTH_ABBR[k-1]:int(v) for k,v in lm.value_counts().sort_index().items()})

pd.DataFrame([{'House':k[0],'Brand':k[1],'PL':k[2],'CFG':k[3],'first':fv,
  'm0':float(A.loc[k,fv]),'y1':float(A.loc[k,tail[:12]].fillna(0).sum()) if len(tail)>=12 else np.nan}
  for k,fv,tail in launches]).to_csv('analysis/out/a3_launches.csv',index=False)
np.save('analysis/out/pool.npy', np.vstack([avg,avg_e,avg_c,pool_n]))
json.dump(out,open('analysis/out/a3_launch.json','w'),indent=1,default=float)
