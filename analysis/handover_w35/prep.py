import pandas as pd, numpy as np

COLS = ['PL','EAN','Desc','Month','C_flag','C_LY','C_sys','C_epos','C_RA','C_TDA','C_cons','C_cuts',
        'P_flag','P_LY','P_sys','P_epos','P_RA','P_TDA','P_cons','P_cuts']
HOR = ['2026.M09','2026.M10','2026.M11','2026.M12','2027.M01','2027.M02','2027.M03','2027.M04']

def load(path='/home/user/DP/handover W35.xlsx'):
    d = pd.read_excel(path, header=[0,1]); d.columns = COLS
    num = [c for c in COLS if c not in ('PL','EAN','Desc','Month')]
    for c in num: d[c] = pd.to_numeric(d[c], errors='coerce').fillna(0.0)
    d['EAN'] = d['EAN'].astype('int64').astype(str)
    d['inHor'] = d['Month'].isin(HOR)
    return d

if __name__ == '__main__':
    d = load()
    h = d[d.inHor]
    print('=== TOTAL HORIZONTE 2026.M09 - 2027.M04 ===')
    for k,lab in [('C_cons','W35 (current)'),('P_cons','W34 (last cycle)'),('C_LY','LY (Consensus Final LY M)')]:
        print(f'{lab:32s} {h[k].sum():>12,.0f}')
    print(f'{"Δ vs LC":32s} {h.C_cons.sum()-h.P_cons.sum():>12,.0f}  ({(h.C_cons.sum()/h.P_cons.sum()-1)*100:+.1f}%)')
    print(f'{"Δ vs LY":32s} {h.C_cons.sum()-h.C_LY.sum():>12,.0f}  ({(h.C_cons.sum()/h.C_LY.sum()-1)*100:+.1f}%)')
    print()
    print('=== POR MES ===')
    m = h.groupby('Month')[['C_LY','P_cons','C_cons','C_sys','P_sys','C_TDA','P_TDA','C_RA','P_RA']].sum()
    m['d_LC']=m.C_cons-m.P_cons; m['d_LC%']=(m.C_cons/m.P_cons-1)*100
    m['d_LY']=m.C_cons-m.C_LY;   m['d_LY%']=(m.C_cons/m.C_LY-1)*100
    print(m[['C_LY','P_cons','C_cons','d_LC','d_LC%','d_LY','d_LY%']].round(0).to_string())
    print()
    print('=== POR PRODUCT LINE ===')
    p = h.groupby('PL')[['C_LY','P_cons','C_cons']].sum()
    p['d_LC']=p.C_cons-p.P_cons; p['d_LC%']=(p.C_cons/p.P_cons.replace(0,np.nan)-1)*100
    p['d_LY']=p.C_cons-p.C_LY;   p['d_LY%']=(p.C_cons/p.C_LY.replace(0,np.nan)-1)*100
    print(p.round(0).to_string())
    print()
    print('=== POR EAN ===')
    e = h.groupby(['PL','EAN','Desc'])[['C_LY','P_cons','C_cons','C_sys','P_sys','C_TDA','P_TDA','C_RA','P_RA']].sum()
    e['d_LC']=e.C_cons-e.P_cons; e['d_LY']=e.C_cons-e.C_LY
    e['d_sys']=e.C_sys-e.P_sys; e['d_TDA']=e.C_TDA-e.P_TDA; e['d_RA']=e.C_RA-e.P_RA
    e['resid_C']=e.C_cons-(e.C_sys+e.C_TDA+e.C_RA); e['resid_P']=e.P_cons-(e.P_sys+e.P_TDA+e.P_RA)
    e['d_resid']=e.resid_C-e.resid_P
    print(e.sort_values('d_LC').round(0).to_string())
