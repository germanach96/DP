import sys, json, os; sys.path.insert(0,'analysis/scripts')
from load import *
from viz import *
from strings import TX, MONTHS
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

LANG=os.environ.get('REPORT_LANG','en')
I=0 if LANG=='en' else 1
def T(k,*a):
    v=TX[k][I]
    return v.format(*a) if a else v
O='analysis/charts/' if LANG=='en' else 'analysis/charts_es/'
os.makedirs(O,exist_ok=True)
df=load(); dfa=load(exclude_multiline=False); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END); L12=window(mc,'2025.M08',HIST_END)
ehist=window(mc,'2024.M07',HIST_END); fwd=window(mc,FWD_START,FWD_END)
A=measure(df,'Actuals'); E=measure(df,'EPOS'); SC=measure(df,'Supply Cuts'); C=measure(df,'Consensus - Final')
J=lambda f: json.load(open(f'analysis/out/{f}'))
s1=J('a1_seasonality.json'); s2=J('a2_epos.json'); s3=J('a3_launch.json'); s4=J('a4.json'); s6=J('a6.json'); s7=J('a7.json')
M=MONTHS[LANG]

# ---------- 1. Sell-in vs sell-out seasonality (indexed to a common base: one axis) ----------
fig,ax=base(7.4,3.6)
si=[s1['sellin_index'][str(m)] for m in range(1,13)]
eo=[s1['epos_index'][str(m)] for m in range(1,13)]
x=np.arange(12)
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,si,color=S1,lw=2,marker='o',ms=5,zorder=4,label=T('c01.l1'))
ax.plot(x,eo,color=S2,lw=2,marker='s',ms=5,zorder=4,label=T('c01.l2'))
ax.annotate(T('c01.a1'),xy=(8,si[8]),xytext=(6.4,178),fontsize=8,color=S1,
            ha='center',arrowprops=dict(arrowstyle='-',color=S1,lw=1))
ax.annotate(T('c01.a2'),xy=(11,eo[11]),xytext=(9.0,196),fontsize=8,color=S2,
            ha='center',arrowprops=dict(arrowstyle='-',color=S2,lw=1))
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,300)
ax.legend(loc='upper left',ncol=1,handlelength=1.4)
finish(fig,ax,T('c01.t'),T('c01.s'),T('c01.y'),O+'c01_season.png')

# ---------- 2. Year-on-year repeatability of the sell-in shape ----------
fig,ax=base(7.4,3.2)
y24=[s1['sellin_by_year']['2024'][str(m)] for m in range(1,13)]
y25=[s1['sellin_by_year']['2025'][str(m)] for m in range(1,13)]
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,y24,color=S1,lw=2,marker='o',ms=4.5,zorder=4,label='2024')
ax.plot(x,y25,color=S2,lw=2,marker='s',ms=4.5,zorder=4,label='2025')
for i in (2,5,8):
    ax.axvspan(i-0.4,i+0.4,color=GRID,alpha=.55,zorder=1)
ax.text(5,150,T('c02.n'),fontsize=8,color=INK2,ha='center')
ax.set_xticks(x); ax.set_xticklabels(M)
finish(fig,ax,T('c02.t'),T('c02.s'),T('c01.y'),O+'c02_yoy.png',legend=True,ncol=2)

# ---------- 3. Lead-lag ----------
fig,ax=base(6.6,3.0)
per=[(k,v) for k,v in sorted(s2['lag_dist'].items(),key=lambda t:int(t[0]))]
xs=[int(k) for k,v in per]; ys=[v for k,v in per]
cols=[S1 if k!=3 else S2 for k in xs]
bars(ax,xs,ys,color=cols,labels=[f'{v}' for v in ys])
ax.set_xticks(xs); ax.set_xticklabels([T('c03.x',k) for k in xs])
ax.text(3,max(ys)*0.72,T('c03.a'),fontsize=8,color=S2,ha='center')
finish(fig,ax,T('c03.t'),T('c03.s',sum(ys),f"{s2['lag_wmean']:.1f}"),T('c03.y'),O+'c03_lag.png')

# ---------- 4. Launch curve ----------
fig,ax=base(7.4,3.4)
cur=s3['pooled_curve']; ks=sorted(int(k) for k in cur)[:12]
idx=[cur[str(k)]['idx'] for k in ks]
cum=[cur[str(k)]['cum'] for k in ks]
bars(ax,ks,idx,color=[S1 if k>0 else S2 for k in ks],
     labels=[f'{v:.0f}' if k in (0,1,2,5,11) else None for k,v in zip(ks,idx)])
ax.axhline(100,color=AXIS,lw=1,ls=(0,(4,3)),zorder=2)
ax.text(11.4,104,T('c04.r'),fontsize=7.5,color=MUTED,ha='right')
ax.set_xticks(ks); ax.set_xticklabels([f'M{k}' for k in ks])
ax.set_ylim(0,300)
ax.annotate(T('c04.a',f"{s3['m0_multiple']:.1f}"),xy=(0,270),xytext=(2.4,258),
            fontsize=8,color=S2,arrowprops=dict(arrowstyle='->',color=S2,lw=1))
finish(fig,ax,T('c04.t'),T('c04.s',s3['n_launches']),T('c04.y'),O+'c04_launch.png')

# ---------- 5. Launch: where the consumer actually shows up ----------
fig,ax=base(7.4,3.4)
ramp=s3['epos_ramp']; kk=[k for k in ks if str(k) in ramp]
si_n=np.array([cur[str(k)]['avg'] for k in kk]); si_n=si_n/si_n.mean()*100
ep_n=np.array([ramp[str(k)]['epos'] for k in kk]); ep_n=ep_n/ep_n.mean()*100
ax.plot(kk,si_n,color=S1,lw=2,marker='o',ms=5,zorder=4,label=T('c05.l1'))
ax.plot(kk,ep_n,color=S2,lw=2,marker='s',ms=5,zorder=4,label='EPOS')
ax.axvline(0,color=S1,lw=1,ls=(0,(3,3)),zorder=2); ax.axvline(3,color=S2,lw=1,ls=(0,(3,3)),zorder=2)
ax.annotate('',xy=(0,238),xytext=(3,238),arrowprops=dict(arrowstyle='<->',color=INK2,lw=1.1))
ax.text(1.5,244,T('c05.g'),fontsize=8,color=INK,ha='center',weight='bold')
ax.set_xticks(kk); ax.set_xticklabels([f'M{k}' for k in kk]); ax.set_ylim(0,275)
finish(fig,ax,T('c05.t'),T('c05.s'),T('c05.y'),O+'c05_launch_epos.png',legend=True,ncol=2)

# ---------- 6. Launch cut rate ----------
fig,ax=base(7.4,3.2)
lc=s3['launch_cuts']; kk2=sorted(int(k) for k in lc)
rates=[lc[str(k)]['rate']*100 for k in kk2]
cols=[status_color(r,3,7,11) for r in rates]
bars(ax,kk2,rates,color=cols,labels=[f'{r:.0f}%' for r in rates])
ax.axvspan(2.5,6.5,color=GRID,alpha=.5,zorder=1)
ax.text(4.5,17.4,T('c06.a'),fontsize=8,color=INK2,ha='center')
ax.set_xticks(kk2); ax.set_xticklabels([f'M{k}' for k in kk2]); ax.set_ylim(0,19)
ax.set_xlim(-0.6,len(kk2)-0.4)
finish(fig,ax,T('c06.t'),T('c06.s'),T('c06.y'),O+'c06_launch_cuts.png')

# ---------- 7. Cut rate by calendar month ----------
fig,ax=base(7.4,3.2)
cmn=[s4['cuts_month'][str(m)]*100 for m in range(1,13)]
cols=[status_color(r,4,7,10) for r in cmn]
bars(ax,x,cmn,color=cols,labels=[f'{r:.0f}%' for r in cmn])
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,13.5)
for i in (2,8):
    ax.text(i,cmn[i]+1.1,T('c07.a'),fontsize=7,color=CRIT,ha='center')
finish(fig,ax,T('c07.t'),T('c07.s'),T('c06.y'),O+'c07_cuts_month.png')

# ---------- 8. Cut rate by house ----------
fig,ax=base(7.0,2.9)
ch=s4['cuts_house']; it=sorted(ch.items(),key=lambda t:-t[1])
hbars(ax,[k for k,v in it],[v*100 for k,v in it],
      color=[status_color(v*100,4,10,18) for k,v in it],
      note=[f'{v:.1%}' for k,v in it])
ax.set_xlabel(T('c06.y'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c08.t'),T('c08.s'),None,O+'c08_cuts_house.png')

# ---------- 9. Forward book vs run rate ----------
fig,ax=base(7.0,3.2)
fy=s4['fwd_year']; run=12256939/12
ys2=[fy[y]['units']/fy[y]['months'] for y in ['2026','2027','2028','2029']]
cols=[status_color(abs(v/run-1)*100,25,50,75) for v in ys2]
bars(ax,np.arange(4),ys2,color=cols,labels=[f'{v/run:.0%}' for v in ys2])
ax.axhline(run,color=INK2,lw=1.4,ls=(0,(4,3)),zorder=5)
ax.text(3.42,run*1.06,T('c09.r'),fontsize=8,color=INK2,ha='right')
ax.set_xticks(np.arange(4)); ax.set_xticklabels(TX['c09.x'][I])
ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
finish(fig,ax,T('c09.t'),T('c09.s'),T('c09.y'),O+'c09_fwdbook.png')

# ---------- 10. Layer composition ----------
fig,ax=base(7.2,3.0)
comp=s4['fwd_comp']; tot=s4['fwd_total']
names=['System FC - Final','Initiative Forecast','Total Demand Assumption','Prometheus Fcst Consensus','Reasonability Adjustment']
vals=[comp[n]/tot*100 for n in names]
names=names+[T('c10.res')]; vals=vals+[comp['__residual__']/tot*100]
cols=[S1,S3,S4,S5,S2,MUTED]
hbars(ax,[n.replace(' - Final','').replace(' Fcst Consensus','') for n in names],vals,color=cols,
      note=[f'{v:+.1f}%' for v in vals])
ax.set_xlim(min(0,min(vals))*1.3,max(vals)*1.25)
ax.axvline(0,color=AXIS,lw=1)
ax.set_xlabel(T('c10.x'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c10.t'),T('c10.s'),None,O+'c10_layers.png')

# ---------- 11. Archetypes ----------
fig,ax=base(7.2,3.2)
order=['STABLE & REPEATABLE','MODERATE','DECLINING','LUMPY / EVENT-DRIVEN','NEW / LAUNCH','INTERMITTENT']
su=s6['summary']; order=[o for o in order if o in su]
ARCH=dict(zip(['STABLE & REPEATABLE','MODERATE','DECLINING','LUMPY / EVENT-DRIVEN',
                'NEW / LAUNCH','INTERMITTENT'],TX['c11.n'][I]))
hbars(ax,[ARCH[o] for o in order],[su[o]['vol_sh']*100 for o in order],
      color=[GOOD,S1,S4,SERIOUS,CRIT,MUTED],
      note=[T('c11.f',f"{su[o]['vol_sh']:.0%}",su[o]['n'],f"{su[o]['cv']:.2f}") for o in order])
ax.set_xlabel(T('c11.x'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c11.t'),T('c11.s'),None,O+'c11_arch.png')

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
ax.set_title(T('c12.t'),loc='left',pad=24)
ax.text(0,1.03,T('c12.s'),
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
    ax.annotate(T('c13.a',n,lab),xy=(n,cs.values[n-1]),xytext=(n+22,cs.values[n-1]-11),
                fontsize=8,color=S2,arrowprops=dict(arrowstyle='->',color=S2,lw=1))
ax.set_xlim(0,len(cs)); ax.set_ylim(0,104)
ax.set_xlabel(T('c13.x'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c13.t'),T('c13.s'),T('c13.y'),O+'c13_pareto.png')

# ---------- 14. CFG comparison ----------
fig,ax=base(7.4,3.3)
cu=[s1['cfg_index']['P_US_ULTA'][str(m)] for m in range(1,13)]
co=[s1['cfg_index']['P_US_ALL_OTHERS'][str(m)] for m in range(1,13)]
ax.axhline(100,color=AXIS,lw=1,zorder=2)
ax.plot(x,cu,color=S1,lw=2,marker='o',ms=5,zorder=4,label='P_US_ULTA')
ax.plot(x,co,color=S2,lw=2,marker='s',ms=5,zorder=4,label='P_US_ALL_OTHERS')
ax.set_xticks(x); ax.set_xticklabels(M); ax.set_ylim(0,175)
finish(fig,ax,T('c14.t'),T('c14.s'),T('c01.y'),O+'c14_cfg.png',legend=True,ncol=2)

# ---------- 15. Watchlist ----------
s5=J('a5.json')
fig,ax=base(7.2,3.0)
it=sorted(s5.items(),key=lambda t:-t[1]['vol'])
FL=TX['c15.n'][I]
hbars(ax,[FL[k] for k,v in it],[v['vol'] for k,v in it],
      color=[CRIT if k in ('SERVICE-LOSS','LOST-FORECAST','CONSUMER-DECLINE') else SERIOUS if k in ('OVER-BOOKED','HORIZON-CLIFF') else S1 for k,v in it],
      note=[T('c15.f',v['n'],f"{v['vol']/1e3:,.0f}") for k,v in it])
ax.xaxis.set_major_formatter(FuncFormatter(fmt_k))
ax.set_xlabel(T('c15.x'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c15.t'),T('c15.s'),None,O+'c15_watchlist.png')

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
ax.text(163,148,T('c16.d'),fontsize=7.8,color=MUTED,rotation=25,ha='center')
ax.text(-103,196,T('c16.q1'),fontsize=8.5,color=CRIT,ha='left',weight='bold')
ax.text(208,-66,T('c16.q2'),fontsize=8.5,color=GOOD,ha='right',va='top',weight='bold')
ax.set_xlabel(T('c16.x'),fontsize=8.5,color=INK2)
ax.set_ylim(-115,372); ax.set_xlim(-115,215)
ax.legend(loc='upper center',ncol=2,handlelength=1.4,bbox_to_anchor=(0.5,1.005))
finish(fig,ax,T('c16.t'),T('c16.s'),T('c16.y'),O+'c16_momentum.png')

# ---------- 17. Forecastability bands ----------
fig,ax=base(7.0,2.7)
bd=s6['bands']; ordb=['HIGH','GOOD','FAIR','LOW']
BN=TX['c17.n'][I]
hbars(ax,[BN[b] for b in ordb],[bd[b]['sh']*100 for b in ordb],color=[GOOD,S1,WARN,CRIT],
      note=[T('c17.f',f"{bd[b]['sh']:.0%}",bd[b]['n']) for b in ordb])
ax.set_xlabel(T('c11.x'),fontsize=8.5,color=INK2)
finish(fig,ax,T('c17.t'),T('c17.s'),None,O+'c17_bands.png')

# ---------- 18. Multiline ----------
fig,ax=base(7.4,3.0)
Am=measure(dfa,'Actuals'); ml=Am.loc[[k for k in Am.index if k[2]==MULTILINE]]
ser=ml[hist].sum()
ax.plot(range(len(hist)),ser.values,color=S1,lw=1.8,zorder=4)
mx=int(np.argmax(ser.values))
ax.annotate(T('c18.a',f'{ser.values[mx]/1e6:.2f}M'),
            xy=(mx,ser.values[mx]),xytext=(mx-14,ser.values[mx]*0.86),fontsize=8,color=S2,
            arrowprops=dict(arrowstyle='->',color=S2,lw=1))
tk=[i for i,c in enumerate(hist) if mnum(c) in (1,7)]
ax.set_xticks(tk); ax.set_xticklabels([hist[i].replace('.M','-') for i in tk],rotation=45,ha='right')
ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
finish(fig,ax,T('c18.t'),T('c18.s'),T('c18.y'),O+'c18_multiline.png')

print("charts written:")
import os
for f in sorted(os.listdir(O)): print("  ",f)
