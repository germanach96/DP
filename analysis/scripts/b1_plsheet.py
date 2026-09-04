# -*- coding: utf-8 -*-
"""Product-line level action table.

Conventions set by the user:
  - One row per Product Line. CFGs are aggregated, never split.
  - Ownership: an initiative is not this team's until a full year of shipments
    has passed. Under a year, the forecast belongs to another department.
      first shipment  < 6 months ago   -> Iniciativa - Local
      first shipment  6 to 12 months   -> Iniciativa - Global
      first shipment  >= 12 months     -> Base
  - Fiscal year runs July to June. "This fiscal" = FY27 = 2026.M07 - 2027.M06.
  - Gucci and Gucci Make up exit the licence at 2027.M06: shipments stop, so a
    forecast ending there is correct and must not be flagged as a gap.
"""
import sys, json; sys.path.insert(0,'analysis/scripts')
from load import *

NOW='2026.M09'                       # current (partial) month
FY_START, FY_END = '2026.M07','2027.M06'      # FY27
PY_START, PY_END = '2025.M07','2026.M06'      # FY26, same months
LICENCE_END='2027.M06'
LICENCE_HOUSES={'Gucci','Gucci Make up'}
MES=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto',
     'Septiembre','Octubre','Noviembre','Diciembre']
ABBR=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

def months_between(a,b):
    ya,ma=int(a[:4]),mnum(a); yb,mb=int(b[:4]),mnum(b)
    return (yb-ya)*12+(mb-ma)

df=load(); mc=month_cols(df)
hist=window(mc,HIST_START,HIST_END)
L12=window(mc,'2025.M08',HIST_END); P12=window(mc,'2024.M08','2025.M07')
L6 =window(mc,'2026.M02',HIST_END); P6=window(mc,'2025.M08','2026.M01')
fy =window(mc,FY_START,FY_END); py=window(mc,PY_START,PY_END)
fwd=window(mc,'2026.M08','2029.M07')

A=measure(df,'Actuals'); C=measure(df,'Consensus - Final')
E=measure(df,'EPOS');    SC=measure(df,'Supply Cuts')
S=measure(df,'System FC - Final')

def bypl(M):
    """Collapse a measure to Product Line, summing over CFG."""
    g=M.groupby(level=['House','Brand','Product Line']).sum(min_count=1)
    return g

Ap,Cp,Ep,SCp = bypl(A),bypl(C),bypl(E),bypl(SC)
keys=Ap.index.union(Cp.index)
rows=[]
for k in keys:
    house,brand,pl=k
    a  = Ap.loc[k] if k in Ap.index else pd.Series(0,index=mc)
    c  = Cp.loc[k] if k in Cp.index else pd.Series(np.nan,index=mc)
    e  = Ep.loc[k] if k in Ep.index else pd.Series(np.nan,index=mc)
    sc = SCp.loc[k] if k in SCp.index else pd.Series(np.nan,index=mc)

    first = a[hist].replace(0,np.nan).first_valid_index()
    age = months_between(first,NOW) if first else None
    if first is None:                cls='Sin envíos'
    elif age < 6:                    cls='Iniciativa - Local'
    elif age < 12:                   cls='Iniciativa - Global'
    else:                            cls='Base'
    owner = 'Tuyo' if cls=='Base' else ('—' if cls=='Sin envíos' else 'Otro depto.')
    # month the team takes ownership = first shipment + 12
    if first:
        y0,m0=int(first[:4]),mnum(first); tot=(y0*12+m0-1)+12
        hand=f'{tot//12}.M{tot%12+1:02d}'
    else: hand=''

    v12 = float(a[L12].sum()); vp12=float(a[P12].sum())
    yoy = (v12-vp12)/vp12 if vp12>0 else np.nan
    # FY27: closed months use actuals, open months use consensus
    fy_v=0.0
    for m in fy:
        fy_v += float(a[m]) if (m<=HIST_END and a[m]==a[m]) else (float(c[m]) if c[m]==c[m] else 0.0)
    py_v = float(a[py].sum())
    fy_ratio = fy_v/py_v if py_v>0 else np.nan
    run_ratio = fy_v/v12 if v12>0 else np.nan

    cuts12=float(sc[L12].sum()) if sc[L12].notna().any() else 0.0
    cut_rate = cuts12/(v12+cuts12) if (v12+cuts12)>0 else 0.0

    has_e = bool(e[L12].notna().any() and e[L12].sum()>0)
    e6,ep6 = float(e[L6].sum()), float(e[P6].sum())
    epos_g = (e6-ep6)/ep6 if ep6>0 else np.nan
    a6,ap6 = float(a[L6].sum()), float(a[P6].sum())
    sell_g = (a6-ap6)/ap6 if ap6>0 else np.nan
    gap = sell_g-epos_g if (sell_g==sell_g and epos_g==epos_g) else np.nan

    # behaviour metrics on the last 24 months
    L24=window(mc,'2024.M08',HIST_END)
    v=a[L24].fillna(0).values.astype(float)
    active=float((v>0).mean()); mu=v.mean()
    cv=float(v.std()/mu) if mu>0 else np.nan
    y1=a[window(mc,'2024.M08','2025.M07')].fillna(0).values.astype(float)
    y2=a[window(mc,'2025.M08','2026.M07')].fillna(0).values.astype(float)
    rep=float(np.corrcoef(y1,y2)[0,1]) if y1.std()>0 and y2.std()>0 else np.nan

    idx,_=seasonal_index(a[hist].to_dict(),[2024,2025])
    if idx:
        top=sorted(idx.items(),key=lambda t:-t[1])[:3]
        peaks=', '.join(ABBR[m-1] for m,_ in top)
        peak_idx=float(top[0][1]); peak_m=ABBR[top[0][0]-1]
    else:
        peaks=''; peak_idx=np.nan; peak_m=''
    licence = 'Sale FY27' if house in LICENCE_HOUSES else 'Continúa'
    lastc = c[fwd].replace(0,np.nan).last_valid_index()

    rows.append(dict(House=house,Brand=brand,PL=pl,cls=cls,owner=owner,
        first=first or '',launch_mes=MES[mnum(first)-1] if first else '',
        age=age,handover=hand,licence=licence,last_cons=lastc or '',
        v12=v12,yoy=yoy,fy=fy_v,py=py_v,fy_ratio=fy_ratio,run_ratio=run_ratio,
        cuts=cuts12,cut_rate=cut_rate,active=active,cv=cv,rep=rep,
        peaks=peaks,peak_m=peak_m,peak_idx=peak_idx,
        has_epos=has_e,epos_g=epos_g,sell_g=sell_g,gap=gap,
        fwd_total=float(c[fwd].sum())))
R=pd.DataFrame(rows)
R['share']=R.v12/R.v12.sum()
R=R.sort_values('v12',ascending=False).reset_index(drop=True)
R.to_pickle('analysis/out/b1_pl.pkl')
print(f"Product lines: {len(R)}   volumen U12M: {R.v12.sum():,.0f}")
print(R.groupby('cls').agg(lineas=('PL','size'),volumen=('v12','sum'),
      share=('share','sum')).to_string(formatters={'volumen':'{:,.0f}'.format,'share':'{:.1%}'.format}))
print()
print("Por licencia:")
print(R.groupby('licence').agg(lineas=('PL','size'),volumen=('v12','sum'),
      share=('share','sum'),fy27=('fy','sum')).to_string(
      formatters={'volumen':'{:,.0f}'.format,'share':'{:.1%}'.format,'fy27':'{:,.0f}'.format}))
print()
print(f"FY27 total (Jul26-Jun27): {R.fy.sum():,.0f}   FY26 mismo periodo: {R.py.sum():,.0f}   "
      f"ratio {R.fy.sum()/R.py.sum():.1%}")
