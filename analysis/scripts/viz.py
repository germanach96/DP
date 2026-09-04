"""Chart toolkit. Palette is the dataviz reference instance, light surface,
validated with scripts/validate_palette.js:
  2-slot adjacent  -> ALL PASS
  3-slot all-pairs -> ALL PASS (aqua sub-3:1 -> relief rule: direct labels)
Rules honoured: one axis only (two measures are indexed to a common base),
categorical hues in fixed order, thin marks, recessive grid, legend for >=2
series with direct labels, status colours reserved and always label-paired.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

S1,S2,S3,S4,S5 = '#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4'
GOOD,WARN,SERIOUS,CRIT = '#0ca30c','#fab219','#ec835a','#d03b3b'
SURFACE='#fcfcfb'; PAGE='#f9f9f7'
INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'; AXIS='#c3c2b7'
SEQ=['#cde2fb','#b7d3f6','#9ec5f4','#86b6ef','#6da7ec','#5598e7','#3987e5','#2a78d6','#256abf','#1c5cab','#184f95','#104281','#0d366b']
DIV_LO='#2a78d6'; DIV_MID='#f0efec'; DIV_HI='#d03b3b'

plt.rcParams.update({
    'font.family':'DejaVu Sans','font.size':9,
    'figure.facecolor':SURFACE,'axes.facecolor':SURFACE,'savefig.facecolor':SURFACE,
    'axes.edgecolor':AXIS,'axes.linewidth':0.8,'axes.labelcolor':INK2,
    'xtick.color':MUTED,'ytick.color':MUTED,'xtick.labelsize':8.5,'ytick.labelsize':8.5,
    'axes.titlesize':11,'axes.titleweight':'bold','axes.titlecolor':INK,
    'grid.color':GRID,'grid.linewidth':0.7,'legend.frameon':False,'legend.fontsize':8.5,
    'axes.spines.top':False,'axes.spines.right':False,
})

def fmt_k(x,_):
    if abs(x)>=1e6: return f'{x/1e6:.1f}M'
    if abs(x)>=1e3: return f'{x/1e3:.0f}K'
    return f'{x:.0f}'

def base(w=7.4,h=3.5,grid='y'):
    fig,ax=plt.subplots(figsize=(w,h))
    if grid: ax.grid(axis=grid,zorder=0)
    ax.set_axisbelow(True)
    return fig,ax

def finish(fig,ax,title=None,sub=None,ylab=None,path=None,legend=False,ncol=4):
    if ylab: ax.set_ylabel(ylab,fontsize=8.5,color=INK2)
    if title: ax.set_title(title,pad=16 if sub else 8,loc='left')
    if sub: ax.text(0,1.02,sub,transform=ax.transAxes,fontsize=8.5,color=INK2,va='bottom')
    if legend: ax.legend(loc='upper right',ncol=ncol,handlelength=1.4)
    fig.tight_layout()
    if path:
        fig.savefig(path,dpi=200,bbox_inches='tight',facecolor=SURFACE)
        plt.close(fig)
    return fig

def bars(ax,x,y,color=S1,labels=None,fmt='{:.0f}',rot=0,lblcolor=None,pad=None):
    """Thin bars with 4px-equivalent rounded ends and selective direct labels."""
    b=ax.bar(x,y,color=color,width=0.62,zorder=3,
             linewidth=1.2,edgecolor=SURFACE)   # 2px surface gap between fills
    if labels is not None:
        rng=max(abs(np.nanmax(y)),abs(np.nanmin(y)))
        pad=pad if pad is not None else rng*0.025
        for xi,yi,li in zip(x,y,labels):
            if li is None: continue
            va='bottom' if yi>=0 else 'top'
            ax.text(xi,yi+(pad if yi>=0 else -pad),li,ha='center',va=va,
                    fontsize=7.8,color=lblcolor or INK2,rotation=rot,zorder=4)
    return b

def hbars(ax,labels,vals,color=S1,fmt='{:,.0f}',note=None):
    ypos=np.arange(len(labels))[::-1]
    ax.barh(ypos,vals,color=color if isinstance(color,str) else color,height=0.62,zorder=3,
            linewidth=1.2,edgecolor=SURFACE)
    ax.set_yticks(ypos); ax.set_yticklabels(labels,fontsize=8.5,color=INK2)
    rng=max(abs(np.min(vals)),abs(np.max(vals))) if len(vals) else 1
    for y,v,n in zip(ypos,vals,note if note else [fmt.format(v) for v in vals]):
        # labels sit outside the bar on whichever side the bar grows
        # always label just past the bar's right-hand end, so a negative bar's
        # label lands in the empty gutter right of zero instead of on the y ticks
        off=rng*0.02
        ax.text((v if v>=0 else 0)+off,y,n,va='center',ha='left',
                fontsize=7.8,color=INK2,zorder=4)
    ax.set_xlim(min(0,np.min(vals)*1.35),max(vals)*1.22)
    ax.grid(axis='x'); ax.set_axisbelow(True)
    for s in ('left',): ax.spines[s].set_visible(False)
    return ax

def status_color(v,t_good,t_warn,t_bad,invert=False):
    """Reserved status ramp; callers must pair it with a visible label."""
    if invert: v=-v; t_good,t_warn,t_bad=-t_good,-t_warn,-t_bad
    if v<=t_good: return GOOD
    if v<=t_warn: return WARN
    if v<=t_bad:  return SERIOUS
    return CRIT

def div_color(v,lo,hi,mid=100.0):
    """Diverging blue<->red around a neutral midpoint (seasonal index)."""
    import matplotlib.colors as mc
    if v>=mid:
        t=min((v-mid)/max(hi-mid,1e-6),1.0)
        c=mc.to_rgb(DIV_MID); d=mc.to_rgb(DIV_HI)
    else:
        t=min((mid-v)/max(mid-lo,1e-6),1.0)
        c=mc.to_rgb(DIV_MID); d=mc.to_rgb(DIV_LO)
    return tuple(c[i]+(d[i]-c[i])*t for i in range(3))
