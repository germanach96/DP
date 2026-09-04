import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *
from viz import *
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

O='analysis/charts/'
df=load(); dfa=load(exclude_multiline=False); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); L12=window(mc,'2025.M08',HIST_END)
ehist=window(mc,'2024.M07',HIST_END); fwd=window(mc,FWD_START,FWD_END)
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')
J=lambda f: json.load(open(f'analysis/out/{f}'))
s1=J('a1_seasonality.json'); s2=J('a2_epos.json'); s3=J('a3_launch.json'); s4=J('a4.json'); s6=J('a6.json'); s7=J('a7.json')
M=MONTH_ABBR

# ---------- 1. Sell-in vs sell-out seasonality (indexed to a common base: one axis) ----------
fig,ax=base(7.4,3.6)
si=[s1['sellin_index'][str(m)] for m in range(1,13)]
eo=[s1['epos_index'][str(m)] for m in range(1,13)]
x=np.arange(12)
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,si,color=S1,lw=2,marker='o',ms=5,zorder=4,label='Sell-in (what we ship)')
ax.plot(x,eo,color=S2,lw=2,marker='s',ms=5,zorder=4,label='EPOS (what the consumer buys)')
ax.annotate('Sell-in peaks\nMar / Jun / Sep',xy=(8,si[8]),xytext=(6.4,178),fontsize=8,color=S1,
            ha='center',arrowprops=dict(arrowstyle='-',color=S1,lw=1))
ax.annotate('Consumer peaks\nin December',xy=(11,eo[11]),xytext=(9.0,196),fontsize=8,color=S2,
            ha='center',arrowprops=dict(arrowstyle='-',color=S2,lw=1))
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,300)
ax.legend(loc='upper left',ncol=1,handlelength=1.4)
finish(fig,ax,'We ship on the quarter, the consumer buys at Christmas',
       'Seasonal index, own-year average = 100. Sell-in 2024-2025, EPOS 2025. Excludes Gucci Fragrance Multiline.',
       'Index (100 = average month)',O+'c01_season.png')

# ---------- 2. Year-on-year repeatability of the sell-in shape ----------
fig,ax=base(7.4,3.2)
y24=[s1['sellin_by_year']['2024'][str(m)] for m in range(1,13)]
y25=[s1['sellin_by_year']['2025'][str(m)] for m in range(1,13)]
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,y24,color=S1,lw=2,marker='o',ms=4.5,zorder=4,label='2024')
ax.plot(x,y25,color=S2,lw=2,marker='s',ms=4.5,zorder=4,label='2025')
for i in (2,5,8):
    ax.axvspan(i-0.4,i+0.4,color=GRID,alpha=.55,zorder=1)
ax.text(5,150,'Mar / Jun / Sep repeat in both years',fontsize=8,color=INK2,ha='center')
ax.set_xticks(x); ax.set_xticklabels(M)
finish(fig,ax,'The three quarter-end peaks repeat year on year',
       'Sell-in seasonal index computed separately for each calendar year.',
       'Index (100 = average month)',O+'c02_yoy.png',legend=True,ncol=2)

# ---------- 3. Lead-lag ----------
fig,ax=base(6.6,3.0)
per=[(k,v) for k,v in sorted(s2['lag_dist'].items(),key=lambda t:int(t[0]))]
xs=[int(k) for k,v in per]; ys=[v for k,v in per]
cols=[S1 if k!=3 else S2 for k in xs]
bars(ax,xs,ys,color=cols,labels=[f'{v}' for v in ys])
ax.set_xticks(xs); ax.set_xticklabels([f'{k} mo' for k in xs])
ax.text(3,max(ys)*0.72,'most common:\nsell-in leads by\n3 months',fontsize=8,color=S2,ha='center')
finish(fig,ax,'Sell-in leads consumer offtake by about three months',
       f"Best-fitting lag per product line, {sum(ys)} lines with a usable EPOS signal. Volume-weighted mean {s2['lag_wmean']:.1f} months.",
       'Product lines',O+'c03_lag.png')

# ---------- 4. Launch curve ----------
fig,ax=base(7.4,3.4)
cur=s3['pooled_curve']; ks=sorted(int(k) for k in cur)[:12]
idx=[cur[str(k)]['idx'] for k in ks]
cum=[cur[str(k)]['cum'] for k in ks]
bars(ax,ks,idx,color=[S1 if k>0 else S2 for k in ks],
     labels=[f'{v:.0f}' if k in (0,1,2,5,11) else None for k,v in zip(ks,idx)])
ax.axhline(100,color=AXIS,lw=1,ls=(0,(4,3)),zorder=2)
ax.text(11.4,104,'year-1 average month',fontsize=7.5,color=MUTED,ha='right')
ax.set_xticks(ks); ax.set_xticklabels([f'M{k}' for k in ks])
ax.set_ylim(0,300)
ax.annotate(f"launch month =\n{s3['m0_multiple']:.1f}x an average month",xy=(0,270),xytext=(2.4,258),
            fontsize=8,color=S2,arrowprops=dict(arrowstyle='->',color=S2,lw=1))
finish(fig,ax,'A launch front-loads: month 0 is 2.7x a normal month',
       f"{s3['n_launches']} launches since 2023.M09, aligned on their first shipment. Index: year-1 average month = 100.",
       'Index (year-1 avg month = 100)',O+'c04_launch.png')

# ---------- 5. Launch: where the consumer actually shows up ----------
fig,ax=base(7.4,3.4)
ramp=s3['epos_ramp']; kk=[k for k in ks if str(k) in ramp]
si_n=np.array([cur[str(k)]['avg'] for k in kk]); si_n=si_n/si_n.mean()*100
ep_n=np.array([ramp[str(k)]['epos'] for k in kk]); ep_n=ep_n/ep_n.mean()*100
ax.plot(kk,si_n,color=S1,lw=2,marker='o',ms=5,zorder=4,label='Sell-in')
ax.plot(kk,ep_n,color=S2,lw=2,marker='s',ms=5,zorder=4,label='EPOS')
ax.axvline(0,color=S1,lw=1,ls=(0,(3,3)),zorder=2); ax.axvline(3,color=S2,lw=1,ls=(0,(3,3)),zorder=2)
ax.annotate('',xy=(0,238),xytext=(3,238),arrowprops=dict(arrowstyle='<->',color=INK2,lw=1.1))
ax.text(1.5,244,'3 months',fontsize=8,color=INK,ha='center',weight='bold')
ax.set_xticks(kk); ax.set_xticklabels([f'M{k}' for k in kk]); ax.set_ylim(0,275)
finish(fig,ax,'We fill the pipe in month 0; the consumer arrives in month 3',
       'Both series indexed to their own 12-month average = 100, so they share one axis.',
       'Index (own 12-month avg = 100)',O+'c05_launch_epos.png',legend=True,ncol=2)

# ---------- 6. Launch cut rate ----------
fig,ax=base(7.4,3.2)
lc=s3['launch_cuts']; kk2=sorted(int(k) for k in lc)
rates=[lc[str(k)]['rate']*100 for k in kk2]
cols=[status_color(r,3,7,11) for r in rates]
bars(ax,kk2,rates,color=cols,labels=[f'{r:.0f}%' for r in rates])
ax.axvspan(2.5,6.5,color=GRID,alpha=.5,zorder=1)
ax.text(4.5,17.4,'the consumer is buying here',fontsize=8,color=INK2,ha='center')
ax.set_xticks(kk2); ax.set_xticklabels([f'M{k}' for k in kk2]); ax.set_ylim(0,19)
ax.set_xlim(-0.6,len(kk2)-0.4)
finish(fig,ax,'Service collapses exactly when the launch starts selling through',
       'Demand lost to supply cuts = cuts / (actuals + cuts), pooled across launches. Colour = service status; value labelled on every bar.',
       'Demand lost (%)',O+'c06_launch_cuts.png')

# ---------- 7. Cut rate by calendar month ----------
fig,ax=base(7.4,3.2)
cmn=[s4['cuts_month'][str(m)]*100 for m in range(1,13)]
cols=[status_color(r,4,7,10) for r in cmn]
bars(ax,x,cmn,color=cols,labels=[f'{r:.0f}%' for r in cmn])
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,13.5)
for i in (2,8):
    ax.text(i,cmn[i]+1.1,'sell-in peak',fontsize=7,color=CRIT,ha='center')
finish(fig,ax,'We run out of stock in our own peak months',
       'Demand lost to supply cuts by calendar month, 2024.M01-2026.M07. Colour = service status; value labelled on every bar.',
       'Demand lost (%)',O+'c07_cuts_month.png')

# ---------- 8. Cut rate by house ----------
fig,ax=base(7.0,2.9)
ch=s4['cuts_house']; it=sorted(ch.items(),key=lambda t:-t[1])
hbars(ax,[k for k,v in it],[v*100 for k,v in it],
      color=[status_color(v*100,4,10,18) for k,v in it],
      note=[f'{v:.1%}' for k,v in it])
ax.set_xlabel('Demand lost (%)',fontsize=8.5,color=INK2)
finish(fig,ax,'Two houses carry almost all of the service loss',
       'Demand lost to supply cuts, 2025.M01-2026.M07. Colour = service status; every bar carries its value.',
       None,O+'c08_cuts_house.png')

# ---------- 9. Forward book vs run rate ----------
fig,ax=base(7.0,3.2)
fy=s4['fwd_year']; run=12256939/12
ys2=[fy[y]['units']/fy[y]['months'] for y in ['2026','2027','2028','2029']]
cols=[status_color(abs(v/run-1)*100,25,50,75) for v in ys2]
bars(ax,np.arange(4),ys2,color=cols,labels=[f'{v/run:.0%}' for v in ys2])
ax.axhline(run,color=INK2,lw=1.4,ls=(0,(4,3)),zorder=5)
ax.text(3.42,run*1.06,'current run rate',fontsize=8,color=INK2,ha='right')
ax.set_xticks(np.arange(4)); ax.set_xticklabels(['2026\n(Aug-Dec)','2027','2028','2029\n(Jan-Jul)'])
ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
finish(fig,ax,'The forward book is aggressive near-in and empties out after 2027',
       'Average monthly Consensus - Final vs the last 12 closed months of actuals. Labels show % of run rate.',
       'Units per month',O+'c09_fwdbook.png')

# ---------- 10. Layer composition ----------
fig,ax=base(7.2,3.0)
comp=s4['fwd_comp']; tot=s4['fwd_total']
names=['System FC - Final','Initiative Forecast','Total Demand Assumption','Prometheus Fcst Consensus','Reasonability Adjustment']
vals=[comp[n]/tot*100 for n in names]
names=names+['Not traceable to any layer']; vals=vals+[comp['__residual__']/tot*100]
cols=[S1,S3,S4,S5,S2,MUTED]
hbars(ax,[n.replace(' - Final','').replace(' Fcst Consensus','') for n in names],vals,color=cols,
      note=[f'{v:+.1f}%' for v in vals])
ax.set_xlim(min(0,min(vals))*1.3,max(vals)*1.25)
ax.axvline(0,color=AXIS,lw=1)
ax.set_xlabel('% of the forward Consensus - Final',fontsize=8.5,color=INK2)
finish(fig,ax,'One unit in three of the forward book has no visible origin',
       'Layers as a share of the 2026.M08-2029.M07 consensus (20.2M units). Every bar is labelled.',
       None,O+'c10_layers.png')

# ---------- 11. Archetypes ----------
fig,ax=base(7.2,3.2)
order=['STABLE & REPEATABLE','MODERATE','DECLINING','LUMPY / EVENT-DRIVEN','NEW / LAUNCH','INTERMITTENT']
su=s6['summary']; order=[o for o in order if o in su]
hbars(ax,[o.title() for o in order],[su[o]['vol_sh']*100 for o in order],
      color=[GOOD,S1,S4,SERIOUS,CRIT,MUTED],
      note=[f"{su[o]['vol_sh']:.0%}  ({su[o]['n']} lines, CV {su[o]['cv']:.2f})" for o in order])
ax.set_xlabel('% of last-12-month volume',fontsize=8.5,color=INK2)
finish(fig,ax,'Only 7% of your volume sits on genuinely stable codes',
       'Archetype by volume share. CV = month-to-month volatility; higher means harder to forecast.',
       None,O+'c11_arch.png')

# ---------- 12. House seasonal heatmap (diverging around 100) ----------
hi=s7['house']; houses=sorted(hi,key=lambda h:-hi[h]['vol12'])
fig,ax=plt.subplots(figsize=(7.4,2.9))
mat=np.array([[hi[h]['index'][str(m)] for m in range(1,13)] for h in houses])
clip=np.clip(mat,0,250)
for i in range(len(houses)):
    for j in range(12):
        ax.add_patch(plt.Rectangle((j,i),0.94,0.9,color=div_color(clip[i,j],0,250),lw=0))
        v=mat[i,j]
        ax.text(j+0.47,i+0.45,f'{v:.0f}',ha='center',va='center',fontsize=7.4,
                color='#ffffff' if (v>190 or v<35) else INK)
ax.set_xlim(-0.05,12); ax.set_ylim(len(houses),-0.05)
ax.set_xticks(np.arange(12)+0.47); ax.set_xticklabels(M)
ax.set_yticks(np.arange(len(houses))+0.45); ax.set_yticklabels(houses,fontsize=8.5,color=INK2)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0); ax.grid(False)
ax.set_title('Every house has a different calendar',loc='left',pad=24)
ax.text(0,1.03,'Sell-in seasonal index, 100 = own average month. Blue below 100, red above; numbers printed in every cell.',
        transform=ax.transAxes,fontsize=8.5,color=INK2,va='bottom')
fig.tight_layout(); fig.savefig(O+'c12_heatmap.png',dpi=200,bbox_inches='tight',facecolor=SURFACE); plt.close(fig)

# ---------- 13. Concentration ----------
fig,ax=base(7.2,3.0)
pl=A[L12].sum(axis=1).groupby(level='Product Line').sum().sort_values(ascending=False)
cs=pl.cumsum()/pl.sum()*100
ax.plot(np.arange(1,len(cs)+1),cs.values,color=S1,lw=2,zorder=4)
for thr,lab in [(50,'50%'),(80,'80%')]:
    n=int((cs<thr).sum())+1
    ax.plot([n],[cs.values[n-1]],'o',color=S2,ms=7,zorder=5)
    ax.annotate(f'{n} lines = {lab} of volume',xy=(n,cs.values[n-1]),xytext=(n+22,cs.values[n-1]-11),
                fontsize=8,color=S2,arrowprops=dict(arrowstyle='->',color=S2,lw=1))
ax.set_xlim(0,len(cs)); ax.set_ylim(0,104)
ax.set_xlabel('Product lines, ranked by volume',fontsize=8.5,color=INK2)
finish(fig,ax,'Half your volume sits in a handful of codes',
       'Cumulative share of the last 12 closed months, product lines ranked by volume. Excludes Gucci Fragrance Multiline.',
       'Cumulative % of volume',O+'c13_pareto.png')

# ---------- 14. CFG comparison ----------
fig,ax=base(7.4,3.3)
cu=[s1['cfg_index']['P_US_ULTA'][str(m)] for m in range(1,13)]
co=[s1['cfg_index']['P_US_ALL_OTHERS'][str(m)] for m in range(1,13)]
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,cu,color=S1,lw=2,marker='o',ms=5,zorder=4,label='P_US_ULTA')
ax.plot(x,co,color=S2,lw=2,marker='s',ms=5,zorder=4,label='P_US_ALL_OTHERS')
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,175)
finish(fig,ax,'ULTA and the rest do not peak in the same months',
       'Sell-in seasonal index by customer group, 2024-2025. 100 = own average month.',
       'Index (100 = average month)',O+'c14_cfg.png',legend=True,ncol=2)

# ---------- 15. Watchlist ----------
s5=J('a5.json')
fig,ax=base(7.2,3.0)
it=sorted(s5.items(),key=lambda t:-t[1]['vol'])
hbars(ax,[k.replace('-',' ').title() for k,v in it],[v['vol'] for k,v in it],
      color=[CRIT if k in ('SERVICE-LOSS','LOST-FORECAST','CONSUMER-DECLINE') else SERIOUS if k in ('OVER-BOOKED','HORIZON-CLIFF') else S1 for k,v in it],
      note=[f"{v['n']} lines · {v['vol']/1e3:,.0f}K u" for k,v in it])
ax.xaxis.set_major_formatter(FuncFormatter(fmt_k))
ax.set_xlabel('Units at stake (last 12 closed months)',fontsize=8.5,color=INK2)
finish(fig,ax,'Where the forward book needs a human this month',
       'Volume carried by each risk flag. A line can carry more than one flag.',
       None,O+'c15_watchlist.png')

# ---------- 16. Momentum scatter ----------
D=pd.read_csv('analysis/out/a2_momentum.csv')
fig,ax=base(7.0,3.6,grid=None)
ax.grid(True,zorder=0); ax.set_axisbelow(True)
ax.axhline(0,color=AXIS,lw=1,zorder=2); ax.axvline(0,color=AXIS,lw=1,zorder=2)
for cfg,col,mk in [('P_US_ULTA',S1,'o'),('P_US_ALL_OTHERS',S2,'s')]:
    g=D[D.CFG==cfg]
    ax.scatter(np.clip(g.epos_g,-1,2)*100,np.clip(g.sellin_g,-1,3)*100,s=np.sqrt(g.vol)/2.2,
               color=col,alpha=.75,marker=mk,zorder=4,label=cfg,linewidths=1,edgecolors=SURFACE)
lim=np.linspace(-100,200,10); ax.plot(lim,lim,color=MUTED,lw=1,ls=(0,(4,3)),zorder=3)
ax.text(163,148,'shipping = selling',fontsize=7.8,color=MUTED,rotation=25,ha='center')
ax.text(-103,196,'shipping into inventory',fontsize=8.5,color=CRIT,ha='left',weight='bold')
ax.text(196,-96,'under-shipping demand',fontsize=8.5,color=GOOD,ha='right',weight='bold')
ax.set_xlabel('EPOS growth, last 6m vs prior 6m (%)',fontsize=8.5,color=INK2)
ax.set_ylim(-115,330); ax.set_xlim(-115,215)
ax.legend(loc='upper center',ncol=2,handlelength=1.4,bbox_to_anchor=(0.5,1.005))
finish(fig,ax,'The codes where shipments and consumer demand disagree',
       'Bubble area = volume. Points above the dashed line ship faster than the consumer buys.',
       'Sell-in growth, last 6m vs prior 6m (%)',O+'c16_momentum.png')

# ---------- 17. Forecastability bands ----------
fig,ax=base(7.0,2.7)
bd=s6['bands']; ordb=['HIGH','GOOD','FAIR','LOW']
hbars(ax,ordb,[bd[b]['sh']*100 for b in ordb],color=[GOOD,S1,WARN,CRIT],
      note=[f"{bd[b]['sh']:.0%}  ({bd[b]['n']} lines)" for b in ordb])
ax.set_xlabel('% of last-12-month volume',fontsize=8.5,color=INK2)
finish(fig,ax,'43% of your volume sits on codes the system cannot forecast well',
       'Forecastability score built from volatility, continuity, year-on-year repeatability, history depth and EPOS visibility.',
       None,O+'c17_bands.png')

# ---------- 18. Multiline ----------
fig,ax=base(7.4,3.0)
Am=measure(dfa,'Actuals'); ml=Am.loc[[k for k in Am.index if k[2]==MULTILINE]]
ser=ml[hist].sum()
ax.plot(range(len(hist)),ser.values,color=S1,lw=1.8,zorder=4)
mx=int(np.argmax(ser.values))
ax.annotate(f'{ser.values[mx]/1e6:.2f}M units in one month\n= 11x its own median month',
            xy=(mx,ser.values[mx]),xytext=(mx-14,ser.values[mx]*0.86),fontsize=8,color=S2,
            arrowprops=dict(arrowstyle='->',color=S2,lw=1))
tk=[i for i,c in enumerate(hist) if mnum(c) in (1,7)]
ax.set_xticks(tk); ax.set_xticklabels([hist[i].replace('.M','-') for i in tk],rotation=45,ha='right')
ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
finish(fig,ax,'Gucci Fragrance Multiline is not a product, it behaves like a batch',
       'Monthly sell-in of the excluded catch-all line, 2023.M08-2026.M07.',
       'Units',O+'c18_multiline.png')

print("charts written:")
import os
for f in sorted(os.listdir(O)): print("  ",f)
