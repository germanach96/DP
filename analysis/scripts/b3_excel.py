# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,'analysis/scripts')
import pandas as pd, numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table,TableStyleInfo
from openpyxl.formatting.rule import CellIsRule
from openpyxl.comments import Comment
from load import measure, load, month_cols, window, seasonal_index, HIST_START, HIST_END

R=pd.read_pickle('analysis/out/b2_pl.pkl')
F='Arial'
INK='FF1A1A1A'; MUT='FF6B6A66'
HDR=PatternFill('solid',fgColor='FF1F3864'); HDRF=Font(name=F,size=9,bold=True,color='FFFFFFFF')
BAND=PatternFill('solid',fgColor='FFF2F1EC')
RED=PatternFill('solid',fgColor='FFFBE0E0'); AMB=PatternFill('solid',fgColor='FFFDF3D9')
GRN=PatternFill('solid',fgColor='FFE6F4E6'); BLU=PatternFill('solid',fgColor='FFE7F0FB')
thin=Side(style='thin',color='FFD9D8D2')
BOX=Border(left=thin,right=thin,top=thin,bottom=thin)
wrap=Alignment(wrap_text=True,vertical='top')
ctr=Alignment(horizontal='center',vertical='center')

wb=Workbook(); wb.remove(wb.active)

def header(ws,cols,row=1):
    for j,(name,w) in enumerate(cols,1):
        c=ws.cell(row=row,column=j,value=name)
        c.fill=HDR; c.font=HDRF; c.alignment=Alignment(wrap_text=True,vertical='center',horizontal='center')
        ws.column_dimensions[get_column_letter(j)].width=w
    ws.row_dimensions[row].height=30

# ============================== 1. LÉEME ==============================
ws=wb.create_sheet('Léeme')
ws.sheet_view.showGridLines=False
ws.column_dimensions['A'].width=3
ws.column_dimensions['B'].width=30; ws.column_dimensions['C'].width=96
def line(r,a,b,bold=False,size=10,color=INK,fill=None):
    c1=ws.cell(row=r,column=2,value=a); c2=ws.cell(row=r,column=3,value=b)
    c1.font=Font(name=F,size=size,bold=True,color=color)
    c2.font=Font(name=F,size=size,bold=bold,color=color)
    c2.alignment=wrap
    if fill: c1.fill=fill; c2.fill=fill
    ws.row_dimensions[r].height=None
ws['B2']='Plan de acción por Product Line'
ws['B2'].font=Font(name=F,size=17,bold=True,color=INK)
ws['B3']='Scope O9 · historia cerrada hasta 2026.M07 · FY = julio a junio'
ws['B3'].font=Font(name=F,size=10,color=MUT)
r=5
line(r,'Cómo usar esto','Ve a la pestaña "Plan de acción". Está ordenada por prioridad y luego por volumen. '
     'La columna ACCIÓN te dice qué hacer con cada línea; las demás columnas son la evidencia detrás.');r+=2
line(r,'Prioridad 1','Acción inmediata. Pérdida de servicio, sobre-carga o caída de consumo en códigos grandes.',fill=RED);r+=1
line(r,'Prioridad 2','Este ciclo. Banderas en códigos medianos, más todas las iniciativas en traspaso.',fill=AMB);r+=1
line(r,'Prioridad 3','Revisión de rutina.',fill=BLU);r+=1
line(r,'Prioridad 4','Sin señal de problema. No les dediques tiempo.',fill=GRN);r+=2
line(r,'CLASIFICACIÓN','Por fecha del primer envío, medida contra hoy (2026.M09):',bold=True);r+=1
line(r,'  Iniciativa - Local','Primer envío hace menos de 6 meses. NO es tuya: el forecast lo lleva otro departamento.');r+=1
line(r,'  Iniciativa - Global','Primer envío hace entre 6 y 12 meses. Sigue sin ser tuya, pero el traspaso está cerca.');r+=1
line(r,'  Base','Primer envío hace más de 12 meses. Ya es tuya y ya la puedes pronosticar tú.');r+=1
line(r,'  Sin envíos','Nunca ha embarcado en la historia disponible (desde 2023.M08).');r+=2
line(r,'FY27','Julio 2026 a junio 2027. Julio 2026 ya cerró, así que la cifra es 1 mes de actual + 11 de consensus.');r+=1
line(r,'FY26','Julio 2025 a junio 2026, actuals. Es la base contra la que se compara el FY27.');r+=1
line(r,'Estado FY27','OVER si el FY27 va arriba de 1.6x el FY26; UNDER si va abajo de 0.55x. Ninguno de los dos '
     'es un error por sí solo, pero ambos necesitan un supuesto con nombre detrás.');r+=2
line(r,'LICENCIA','Gucci y Gucci Make up salen de licencia en 2027.M06: dejan de embarcar al cierre del FY27. '
     'Son 109 líneas y el 61% de tu volumen. Que su book termine ahí es correcto, no un hueco.',fill=AMB);r+=2
line(r,'Meses pico','Los 3 meses más altos del índice estacional (100 = mes promedio del propio año), calculado '
     'sobre 2024 y 2025. "Fuerza" es qué tan alto llega el mes número uno.');r+=1
line(r,'Estacionalidad confiable','Sí sólo cuando la forma del año se repite contra el año anterior (correlación > 0.30). '
     'Si dice No, no apliques factor estacional aunque el pico se vea grande.');r+=2
line(r,'Pronosticabilidad','Score 0-100 con volatilidad, continuidad de envíos, repetibilidad año contra año, '
     'profundidad de historia y disponibilidad de EPOS. ALTA/BUENA = el sistema puede; REGULAR/BAJA = necesita tu criterio.');r+=2
line(r,'LO QUE ESTE ARCHIVO NO PUEDE DECIR','O9 sobreescribe la historia: en todo mes cerrado System FC = Consensus = Actuals. '
     'No existe foto del forecast previa al mes, así que NO hay MAPE ni BIAS aquí. Todo esto se apoya en '
     'comportamiento estructural, no en accuracy medida.',fill=AMB);r+=2
line(r,'Sobre los números','Son valores calculados, no fórmulas. Esta hoja es una foto de un análisis sobre el '
     'extract de O9 (3.030 filas); no tiene inputs propios de los cuales recalcular. Si cambia el extract, '
     'hay que regenerar el archivo, no editarlo.');r+=1
line(r,'Fuente','scope analysis.xlsx, hoja SCOPE. Excluye Gucci Fragrance Multiline (00003484), una línea '
     'agrupadora que sola carga el 37% del volumen y distorsiona cualquier promedio.')

# ============================== 2. PLAN DE ACCIÓN ==============================
ws=wb.create_sheet('Plan de acción')
cols=[('Prio',5),('House',17),('Brand',22),('Product Line',34),('Clasificación',15),('Dueño',11),
      ('Licencia',10),('1er envío',9),('Mes launch',11),('Meses',6),('Traspaso',9),
      ('Vol U12M',11),('% scope',8),('vs AA',8),
      ('FY27',11),('FY26',11),('FY27/FY26',9),('Estado FY27',13),
      ('Arquetipo',19),('Score',6),('Banda',9),('¿Confiar en el sistema?',24),
      ('Meses pico',12),('Fuerza',11),('Estac. confiable',11),
      ('Volatilidad',9),('% meses activo',9),('Repetib. AA',9),
      ('EPOS',6),('Tend. EPOS 6m',10),('Brecha sell-in vs EPOS',11),('Dem. perdida',10),
      ('Banderas',26),('ACCIÓN',95)]
header(ws,cols)
D=R.sort_values(['prioridad','v12'],ascending=[True,False]).reset_index(drop=True)
pf={1:RED,2:AMB,3:BLU,4:None}
for i,r_ in enumerate(D.itertuples(),start=2):
    nn=lambda x: None if (x!=x) else x
    vals=[r_.prioridad,r_.House,r_.Brand,r_.PL,r_.cls,r_.owner,r_.licence,r_.first,r_.launch_mes,
          nn(r_.age),r_.handover,r_.v12,r_.share,nn(r_.yoy),r_.fy,r_.py,nn(r_.fy_ratio),r_.estado_fy,
          r_.arquetipo,nn(r_.score),(str(r_.banda) if r_.banda==r_.banda else ''),r_.confiar,
          r_.peaks,r_.fuerza_pico,r_.estac_confiable,nn(r_.cv),nn(r_.active),nn(r_.rep),
          ('Sí' if r_.has_epos else 'No'),nn(r_.epos_g),nn(r_.gap),nn(r_.cut_rate),
          r_.banderas,r_.accion]
    for j,v in enumerate(vals,1):
        c=ws.cell(row=i,column=j,value=v)
        c.font=Font(name=F,size=9,color=INK); c.border=BOX
        c.alignment=wrap if j in (4,34,22,33) else Alignment(vertical='top')
    ws.cell(row=i,column=1).fill=pf[r_.prioridad] or PatternFill()
    ws.cell(row=i,column=1).alignment=ctr
    ws.cell(row=i,column=1).font=Font(name=F,size=10,bold=True,color=INK)
    if r_.licence=='Sale FY27': ws.cell(row=i,column=7).fill=AMB
    for col,st in ((18,r_.estado_fy),):
        if st in ('OVER','UNDER'): ws.cell(row=i,column=col).fill=RED
        elif st in ('Over leve','Under leve'): ws.cell(row=i,column=col).fill=AMB
        elif st=='En línea': ws.cell(row=i,column=col).fill=GRN
    bd=str(r_.banda)
    if bd=='ALTA': ws.cell(row=i,column=21).fill=GRN
    elif bd=='BUENA': ws.cell(row=i,column=21).fill=BLU
    elif bd=='REGULAR': ws.cell(row=i,column=21).fill=AMB
    elif bd=='BAJA': ws.cell(row=i,column=21).fill=RED
    if r_.banderas: ws.cell(row=i,column=33).fill=AMB
    ws.row_dimensions[i].height=46
n=len(D)+1
# Values, not formulas, deliberately: this workbook is a snapshot of an analysis
# over a 3,030-row O9 extract, so it has no in-sheet inputs to recalculate from.
# (LibreOffice is also unavailable in this environment, so formulas could not be
# verified, and openpyxl writes them without cached values.)
for col,fmt in ((12,'#,##0'),(15,'#,##0'),(16,'#,##0')):
    for rr in range(2,n+1): ws.cell(row=rr,column=col).number_format=fmt
for col in (13,14,17,27,28,30,31,32):
    for rr in range(2,n+1): ws.cell(row=rr,column=col).number_format='0%'
for col in (26,):
    for rr in range(2,n+1): ws.cell(row=rr,column=col).number_format='0.00'
ws.freeze_panes='E2'
ws.auto_filter.ref=f'A1:{get_column_letter(len(cols))}{n}'
ws.cell(row=1,column=34).comment=Comment(
  'Recomendación derivada de: clasificación por antigüedad, banderas de riesgo, '
  'pronosticabilidad y estado del FY27. Las iniciativas (<12 meses) no son tuyas: '
  'ahí la acción es de monitoreo y preparación del traspaso.','Análisis de scope')

# ============================== 3. ESTACIONALIDAD ==============================
df=load(); mc=month_cols(df); hist=window(mc,HIST_START,HIST_END)
A=measure(df,'Actuals').groupby(level=['House','Brand','Product Line']).sum(min_count=1)
ABBR=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
ws=wb.create_sheet('Estacionalidad')
cols=[('House',17),('Brand',22),('Product Line',34),('Clasificación',15),('Vol U12M',11)]+\
     [(m,6) for m in ABBR]+[('Mes pico',8),('Fuerza',11),('Confiable',10)]
header(ws,cols)
rr=2
for r_ in R.sort_values('v12',ascending=False).itertuples():
    k=(r_.House,r_.Brand,r_.PL)
    idx,_=seasonal_index(A.loc[k,hist].to_dict(),[2024,2025]) if k in A.index else (None,None)
    vals=[r_.House,r_.Brand,r_.PL,r_.cls,r_.v12]
    vals+=[(round(idx[m]) if idx[m]==idx[m] else None) if idx else None
           for m in range(1,13)]
    vals+=[r_.peak_m,r_.fuerza_pico,r_.estac_confiable]
    for j,v in enumerate(vals,1):
        c=ws.cell(row=rr,column=j,value=v)
        c.font=Font(name=F,size=9,color=INK); c.border=BOX
        c.alignment=wrap if j==3 else Alignment(vertical='center')
        if 6<=j<=17 and v is not None:
            if v>=150: c.fill=PatternFill('solid',fgColor='FFE8A9A9')
            elif v>=125: c.fill=PatternFill('solid',fgColor='FFF6D2C4')
            elif v>=110: c.fill=PatternFill('solid',fgColor='FFFCECDF')
            elif v<=50: c.fill=PatternFill('solid',fgColor='FFCFE0F5')
            elif v<=85: c.fill=PatternFill('solid',fgColor='FFE7F0FB')
            c.alignment=ctr
    ws.cell(row=rr,column=5).number_format='#,##0'
    rr+=1
ws.freeze_panes='D2'
ws.auto_filter.ref=f'A1:{get_column_letter(len(cols))}{rr-1}'
ws.cell(row=1,column=6).comment=Comment(
  'Índice estacional: 100 = mes promedio del propio año. Calculado por año calendario '
  '(2024 y 2025) y luego promediado, para que un año grande no domine la forma. '
  'Vacío = no hay dos años completos de historia.','Análisis de scope')

# ============================== 4. RESUMEN ==============================
ws=wb.create_sheet('Resumen',0)
ws.sheet_view.showGridLines=False
for col,w in (('A',3),('B',30),('C',16),('D',16),('E',16),('F',16),('G',16)):
    ws.column_dimensions[col].width=w
ws['B2']='Resumen del scope'; ws['B2'].font=Font(name=F,size=17,bold=True,color=INK)
ws['B3']='Todas las cifras en unidades. FY = julio a junio.'; ws['B3'].font=Font(name=F,size=10,color=MUT)

def block(r,title,hdrs,rows,fmts=None):
    ws.cell(row=r,column=2,value=title).font=Font(name=F,size=11,bold=True,color=INK)
    r+=1
    for j,h in enumerate(hdrs,2):
        c=ws.cell(row=r,column=j,value=h); c.fill=HDR; c.font=HDRF; c.alignment=ctr
    r+=1
    for row in rows:
        for j,v in enumerate(row,2):
            c=ws.cell(row=r,column=j,value=v)
            c.font=Font(name=F,size=10,color=INK); c.border=BOX
            if fmts and j-2 in fmts: c.number_format=fmts[j-2]
        r+=1
    return r+1

r=5
g=R.groupby('cls').agg(n=('PL','size'),v=('v12','sum'),fy=('fy','sum'))
rows=[[k,int(v.n),float(v.v),float(v.v/R.v12.sum()),float(v.fy)] for k,v in g.iterrows()]
rows.append(['TOTAL',len(R),float(R.v12.sum()),1.0,float(R.fy.sum())])
r=block(r,'Por clasificación (antigüedad del primer envío)',
        ['Clasificación','Líneas','Vol U12M','% scope','FY27'],rows,{2:'#,##0',3:'0.0%',4:'#,##0'})

g=R.groupby('licence').agg(n=('PL','size'),v=('v12','sum'),fy=('fy','sum'))
rows=[[k,int(v.n),float(v.v),float(v.v/R.v12.sum()),float(v.fy)] for k,v in g.iterrows()]
r=block(r,'Por licencia — Gucci y Gucci Make up dejan de embarcar en 2027.M06',
        ['Licencia','Líneas','Vol U12M','% scope','FY27'],rows,{2:'#,##0',3:'0.0%',4:'#,##0'})

g=R.groupby('prioridad').agg(n=('PL','size'),v=('v12','sum'))
lbl={1:'P1 · Acción inmediata',2:'P2 · Este ciclo',3:'P3 · Rutina',4:'P4 · Sin señal'}
rows=[[lbl[k],int(v.n),float(v.v),float(v.v/R.v12.sum())] for k,v in g.iterrows()]
r=block(r,'Por prioridad de revisión',['Prioridad','Líneas','Vol U12M','% scope'],rows,
        {2:'#,##0',3:'0.0%'})

b=R[R.cls=='Base']
g=b.groupby('banda',observed=True).agg(n=('PL','size'),v=('v12','sum'))
rows=[[str(k),int(v.n),float(v.v),float(v.v/b.v12.sum())] for k,v in g.iterrows()]
r=block(r,'Pronosticabilidad — sólo líneas Base (las que sí son tuyas)',
        ['Banda','Líneas','Vol U12M','% de Base'],rows,{2:'#,##0',3:'0.0%'})

g=R.groupby('estado_fy').agg(n=('PL','size'),v=('v12','sum'),fy=('fy','sum')).sort_values('v',ascending=False)
rows=[[k,int(v.n),float(v.v),float(v.fy)] for k,v in g.iterrows()]
r=block(r,'Estado del FY27 contra el mismo periodo del FY26',
        ['Estado','Líneas','Vol U12M','FY27'],rows,{2:'#,##0',3:'#,##0'})

fl=[]
for name in ['Servicio','Sobre-cargado','Sub-cargado','Consumo en caída','Inventario',
             'Fantasma','Forecast perdido']:
    s=R[R.banderas.str.contains(name,na=False)]
    fl.append([name,len(s),float(s.v12.sum()),float(s.fy.sum())])
r=block(r,'Banderas de riesgo (una línea puede tener varias)',
        ['Bandera','Líneas','Vol U12M','FY27'],fl,{2:'#,##0',3:'#,##0'})

ws.cell(row=r,column=2,value='Ojo con el total').font=Font(name=F,size=11,bold=True,color='FF9C4A00')
r+=1
tot=ws.cell(row=r,column=2,value=(
  f'El FY27 completo suma {R.fy.sum():,.0f} u contra {R.py.sum():,.0f} u del mismo periodo del FY26: '
  f'{R.fy.sum()/R.py.sum():.0%}. Estás prometiendo a supply un año 27% mayor al que acabas de entregar, '
  f'y eso incluye 109 líneas que salen de licencia. Vale la pena que ese +27% tenga un dueño y un supuesto.'
  ).replace(',','.'))
tot.font=Font(name=F,size=10,color=INK); tot.alignment=wrap; tot.fill=AMB
ws.merge_cells(start_row=r,start_column=2,end_row=r+2,end_column=7)

wb.save('Plan de accion por Product Line.xlsx')
print('saved')
