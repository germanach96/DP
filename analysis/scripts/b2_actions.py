# -*- coding: utf-8 -*-
"""Turns the product-line table into a concrete recommendation per line."""
import sys; sys.path.insert(0,'analysis/scripts')
import pandas as pd, numpy as np
R=pd.read_pickle('analysis/out/b1_pl.pkl')

def score(r):
    if r.cls=='Sin envíos': return np.nan
    s=0
    s+= 30 if r.cv<0.6 else 20 if r.cv<0.9 else 10 if r.cv<1.3 else 0
    s+= 25 if r.active>0.9 else 15 if r.active>0.7 else 5 if r.active>0.5 else 0
    rp=r.rep if r.rep==r.rep else 0
    s+= 25 if rp>0.5 else 15 if rp>0.25 else 5 if rp>0 else 0
    s+= 10 if (r.age or 0)>=24 else 5 if (r.age or 0)>=12 else 0
    s+= 10 if r.has_epos else 0
    return s
R['score']=R.apply(score,axis=1)
R['banda']=pd.cut(R.score,[-1,39,59,79,100],labels=['BAJA','REGULAR','BUENA','ALTA'])

def arch(r):
    if r.cls=='Sin envíos':           return 'Sin envíos'
    if r.cls!='Base':                 return 'Lanzamiento'
    if r.active<0.5:                  return 'Intermitente'
    if r.cv>1.0:                      return 'Irregular / por evento'
    if r.yoy==r.yoy and r.yoy<-0.35:  return 'En declive'
    if r.cv<=0.6 and (r.rep if r.rep==r.rep else 0)>0.3: return 'Estable y repetible'
    return 'Moderado'
R['arquetipo']=R.apply(arch,axis=1)

def fuerza(v):
    if v!=v: return ''
    return 'Muy fuerte' if v>=150 else 'Fuerte' if v>=125 else 'Moderado' if v>=110 else 'Plano'
R['fuerza_pico']=R.peak_idx.map(fuerza)
R['estac_confiable']=np.where(R.cls!='Base','No aplica',
    np.where((R.rep>0.30)&(R.peak_idx>=110),'Sí','No'))

def confiar(r):
    if r.cls=='Sin envíos':   return 'No aplica — sin historia'
    if r.cls!='Base':         return 'No aplica — no es tuya aún'
    if r.banda=='ALTA':       return 'Sí — dejar correr'
    if r.banda=='BUENA':      return 'Sí — con chequeo estacional'
    if r.banda=='REGULAR':    return 'Parcial — no aceptar sin revisar'
    return 'No — manual'
R['confiar']=R.apply(confiar,axis=1)

def estado_fy(r):
    x=r.fy_ratio
    if x!=x or r.py<=0:
        return 'Sin base comparable' if r.fy>0 else 'Sin forecast'
    if r.v12<3000 and r.py<3000: return 'Volumen bajo'
    if x>1.60: return 'OVER'
    if x<0.55: return 'UNDER'
    if x>1.25: return 'Over leve'
    if x<0.80: return 'Under leve'
    return 'En línea'
R['estado_fy']=R.apply(estado_fy,axis=1)

# ---------------- flags ----------------
def flags(r):
    f=[]
    if r.cut_rate>0.20 and r.cuts>5000:                     f.append('Servicio')
    if r.estado_fy=='OVER':                                 f.append('Sobre-cargado')
    if r.estado_fy=='UNDER':                                f.append('Sub-cargado')
    if r.epos_g==r.epos_g and r.epos_g<-0.25 and r.fy_ratio==r.fy_ratio and r.fy_ratio>0.9 \
       and r.v12>10000:                                     f.append('Consumo en caída')
    if r.gap==r.gap and r.gap>0.25 and r.v12>10000:         f.append('Inventario')
    if r.v12<200 and r.fy>3000:                             f.append('Fantasma')
    if r.v12>3000 and r.fy<r.v12*0.15:                      f.append('Forecast perdido')
    return ' · '.join(f)
R['banderas']=R.apply(flags,axis=1)

# ---------------- the action ----------------
def accion(r):
    v=f'{r.v12:,.0f}'.replace(',','.')
    # 1. never shipped
    if r.cls=='Sin envíos':
        if r.fy>3000:
            return (f'Confirmar fecha de lanzamiento. Hay {r.fy:,.0f} u en el FY27 sin un solo '
                    f'envío en la historia. Si la fecha se movió, el book va a construir para '
                    f'una fecha que ya no existe.').replace(',','.')
        return 'Sin actividad y sin book relevante. Verificar si debe seguir en el scope.'
    # 2. not yours yet
    if r.cls in ('Iniciativa - Local','Iniciativa - Global'):
        base=(f'No es tuya todavía — la toma el otro depto. hasta {r.handover}. ')
        if r.age is not None and r.age<3:
            base+=('Aún no hay lectura válida: el primer EPOS honesto llega en el mes 3. '
                   'No re-pronostiques con datos de mes 1.')
        elif r.age is not None and r.age<6:
            base+=('Mes 3-6: ventana de quiebre. Aquí se pierde 10-15% de la demanda por cuts. '
                   'Vigila la reposición, no el forecast.')
        else:
            base+=(f'Traspaso en {r.handover}: empieza a armar tu baseline. Valida que el book '
                   f'post-traspaso baje al steady state (~21% del mes de lanzamiento), no que '
                   f'siga la curva de lanzamiento.')
        if r.cut_rate>0.15 and r.cuts>3000:
            base+=f' Ojo: ya perdiste {r.cut_rate:.0%} de la demanda por cuts.'
        return base
    # 3. Base — yours
    parts=[]
    if r.licence=='Sale FY27':
        parts.append('Sale de licencia en 2027.M06: el FY27 es el último ciclo completo. '
                     'No extiendas el book más allá y confirma que el fade-out esté planeado.')
    if 'Servicio' in r.banderas:
        parts.append(f'PRIORIDAD: perdiste {r.cut_rate:.0%} de la demanda por cuts '
                     f'({r.cuts:,.0f} u). Esto es demanda ya ganada — es conversación con supply, '
                     f'no ajuste de forecast. Y ojo: los actuals de esos meses están deprimidos, '
                     f'así que el sistema aprendió una base falsa.'.replace(',','.'))
    if 'Consumo en caída' in r.banderas:
        parts.append(f'El EPOS cae {abs(r.epos_g):.0%} en 6 meses pero el FY27 está a '
                     f'{r.fy_ratio:.0%} del año pasado. Las dos cosas no pueden ser ciertas: '
                     f'baja el forecast o explica por qué el consumo se recupera.')
    elif 'Inventario' in r.banderas:
        parts.append(f'Embarcas {r.gap*100:+.0f} pp más rápido de lo que compra el consumidor. '
                     f'Estás llenando al retailer. Mantén plano en vez de extrapolar.')
    if 'Sobre-cargado' in r.banderas:
        parts.append(f'FY27 a {r.fy_ratio:.0%} del mismo periodo del año pasado. Necesita un '
                     f'supuesto con nombre (lanzamiento, promo, distribución nueva). Si nadie '
                     f'lo puede nombrar, bájalo.')
    if 'Sub-cargado' in r.banderas:
        parts.append(f'FY27 a solo {r.fy_ratio:.0%} del año pasado. Si no hay delisting '
                     f'confirmado, supply se va a quedar corto.')
    if 'Forecast perdido' in r.banderas and 'Sub-cargado' not in r.banderas:
        parts.append('Sigue vendiendo pero el FY27 está prácticamente vacío. Revisar si es un '
                     'hueco de mantenimiento.')
    if not parts:
        if r.banda=='ALTA':
            parts.append(f'Sana. Deja correr el System FC y revisa trimestral. Perfil estacional '
                         f'confiable: refuerza {r.peaks}.')
        elif r.banda=='BUENA':
            parts.append(f'Confía en el System FC pero valida el perfil estacional ({r.peaks}) '
                         f'antes de cerrar el ciclo.')
        elif r.banda=='REGULAR':
            parts.append(f'No aceptes el número del sistema sin mirarlo. Ancla en un total anual '
                         f'y fasealo tú; el mes a mes del sistema aquí es ruido.')
        else:
            parts.append('Manual. El sistema no tiene patrón que aprender: fija volumen anual y '
                         'reparte según el patrón de pedido real, no con una curva suave.')
    if r.estac_confiable=='No' and r.banda in ('ALTA','BUENA') and r.arquetipo!='Estable y repetible':
        parts.append('No apliques factor estacional: la forma no se repite año contra año.')
    return ' '.join(parts)
R['accion']=R.apply(accion,axis=1)

def prio(r):
    if 'Servicio' in r.banderas and r.v12>20000:            return 1
    if r.cls=='Base' and ('Consumo en caída' in r.banderas
        or 'Sobre-cargado' in r.banderas) and r.v12>50000:  return 1
    if 'Forecast perdido' in r.banderas and r.v12>20000:    return 1
    if r.banderas and r.v12>10000:                          return 2
    if r.cls!='Base' and r.cls!='Sin envíos':               return 2
    if r.banderas or r.fy>3000:                             return 3
    return 4
R['prioridad']=R.apply(prio,axis=1)
R.to_pickle('analysis/out/b2_pl.pkl')

print("Clasificación x prioridad:")
print(pd.crosstab(R.cls,R.prioridad,margins=True).to_string())
print("\nEstado FY27:")
print(R.groupby('estado_fy').agg(n=('PL','size'),vol=('v12','sum')).sort_values('vol',ascending=False)
      .to_string(formatters={'vol':'{:,.0f}'.format}))
print("\nBanda de pronosticabilidad (solo Base):")
b=R[R.cls=='Base']
print(b.groupby('banda',observed=True).agg(n=('PL','size'),vol=('v12','sum')).to_string(formatters={'vol':'{:,.0f}'.format}))
print("\nP1 (acción inmediata):",int((R.prioridad==1).sum()),"líneas,",f"{R[R.prioridad==1].v12.sum():,.0f} u")
print(R[R.prioridad==1][['House','PL','cls','v12','banderas']].head(12).to_string(index=False))
