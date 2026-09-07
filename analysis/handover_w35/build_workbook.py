# -*- coding: utf-8 -*-
"""Construye el workbook de comparacion Handover W35 vs W34 (Kylie MU).

Fuente: 'handover W35.xlsx' (extraccion O9, dos vistas: CurrentWorkingView = W35,
Month-2026.M08.W34(Recovered) = ciclo anterior). Horizonte de foco: 2026.M09 - 2027.M04.
Todas las celdas de calculo del workbook son formulas contra la hoja 'Datos'.
"""
import pandas as pd, numpy as np, os, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep import load, HOR

ROOT = '/home/user/DP'
OUT  = os.path.join(ROOT, 'Handover W35 vs W34 - Kylie MU.xlsx')

QMAP = {'2026.M09':'FY27 Q1','2026.M10':'FY27 Q2','2026.M11':'FY27 Q2','2026.M12':'FY27 Q2',
        '2027.M01':'FY27 Q3','2027.M02':'FY27 Q3','2027.M03':'FY27 Q3','2027.M04':'FY27 Q4',
        '2026.M07':'FY26 Q4','2026.M08':'FY27 Q1','2027.M05':'FY27 Q4','2027.M06':'FY27 Q4'}
QORDER = ['FY27 Q1','FY27 Q2','FY27 Q3','FY27 Q4']

# ---------- estilos ----------
F  = 'Arial'
NAVY   = '1F3864'; BLUEH = 'D9E2F3'; GREY = 'F2F2F2'; AMBER = 'FFF2CC'; GREEN='E2EFDA'; RED='FCE4E4'
h1 = Font(name=F, size=16, bold=True, color=NAVY)
h2 = Font(name=F, size=12, bold=True, color=NAVY)
hdr= Font(name=F, size=9,  bold=True, color='FFFFFF')
bod= Font(name=F, size=10)
bodb=Font(name=F, size=10, bold=True)
small=Font(name=F, size=9, italic=True, color='595959')
fill_hdr = PatternFill('solid', fgColor=NAVY)
fill_tot = PatternFill('solid', fgColor=BLUEH)
fill_amb = PatternFill('solid', fgColor=AMBER)
fill_grn = PatternFill('solid', fgColor=GREEN)
fill_red = PatternFill('solid', fgColor=RED)
thin = Side(style='thin', color='BFBFBF')
box  = Border(left=thin, right=thin, top=thin, bottom=thin)

NUM = '#,##0;[Red](#,##0);-'
PCT = '0.0%;[Red](0.0%);-'

def put(ws, cell, val, font=bod, fmt=None, fill=None, align=None, border=True, wrap=False):
    c = ws[cell]; c.value = val; c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if align or wrap: c.alignment = Alignment(horizontal=align or 'general', vertical='center', wrap_text=wrap)
    if border: c.border = box
    return c

def header_row(ws, row, labels, start=1, widths=None):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start+i, value=lab)
        c.font = hdr; c.fill = fill_hdr; c.border = box
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[row].height = 30
    if widths:
        for i, w in enumerate(widths):
            ws.column_dimensions[get_column_letter(start+i)].width = w

def title(ws, text, sub=None):
    put(ws, 'A1', text, font=h1, border=False)
    if sub: put(ws, 'A2', sub, font=small, border=False)
    ws.row_dimensions[1].height = 22

# ---------- datos ----------
d = load()
d['Trimestre'] = d['Month'].map(QMAP)
d['EnHorizonte'] = d['inHor'].astype(int)
d['Modo'] = np.where(d['C_flag'] == 2, 'Manual', 'Sistema')
d = d.sort_values(['PL', 'EAN', 'Month']).reset_index(drop=True)

EANS = (d[d.inHor].groupby(['PL','EAN','Desc'], as_index=False)
          .agg(C=('C_cons','sum'), P=('P_cons','sum'), LY=('C_LY','sum')))
EANS['dLC'] = EANS.C - EANS.P
EANS = EANS.reindex(EANS.dLC.abs().sort_values(ascending=False).index).reset_index(drop=True)
PLS = list(d.PL.unique())

wb = Workbook(); wb.remove(wb.active)

# =========================================================================
# HOJA: Datos
# =========================================================================
ws = wb.create_sheet('Datos')
cols = ['Product Line','EAN','Planning Item Description','Mes','Trimestre FY','En Horizonte',
        'Modo forecast','W35 Consensus','W35 System FC','W35 Reasonability Adj','W35 Total Dem. Assumption',
        'W35 Ignore SysFC Flag','W35 EPOS','W35 Supply Cuts',
        'W34 Consensus','W34 System FC','W34 Reasonability Adj','W34 Total Dem. Assumption','W34 Ignore SysFC Flag',
        'Consensus Final LY M','Delta vs LC (u)','Delta vs LY (u)']
header_row(ws, 1, cols, widths=[30,16,42,11,11,11,11]+[13]*15)
src = ['PL','EAN','Desc','Month','Trimestre','EnHorizonte','Modo','C_cons','C_sys','C_RA','C_TDA','C_flag',
       'C_epos','C_cuts','P_cons','P_sys','P_RA','P_TDA','P_flag','C_LY']
for r, (_, row) in enumerate(d.iterrows(), start=2):
    for i, k in enumerate(src, start=1):
        v = row[k]
        c = ws.cell(row=r, column=i, value=(str(v) if k == 'EAN' else v))
        c.font = bod; c.border = box
        if i >= 8: c.number_format = NUM
    ws.cell(row=r, column=21, value=f'=H{r}-O{r}').font = bod
    ws.cell(row=r, column=22, value=f'=H{r}-T{r}').font = bod
    for i in (21, 22):
        ws.cell(row=r, column=i).number_format = NUM; ws.cell(row=r, column=i).border = box
NR = len(d) + 1
ws.freeze_panes = 'E2'; ws.auto_filter.ref = f'A1:V{NR}'

# rangos absolutos reutilizables
R = lambda col: f"Datos!${col}$2:${col}${NR}"
PL_, EAN_, DESC_, MES_, TRI_, HOR_, MODO_ = (R('A'), R('B'), R('C'), R('D'), R('E'), R('F'), R('G'))
W35C, W35S, W35RA, W35TDA = R('H'), R('I'), R('J'), R('K')
W34C, W34S, W34RA, W34TDA = R('O'), R('P'), R('Q'), R('R')
LYC = R('T')
HC = f'{HOR_},1'          # criterio: en horizonte
SIS = '"Sistema"'
MAN = '"Manual"'

def sif(rng, *crit):
    return f'SUMIFS({rng},{",".join(crit)})'

# =========================================================================
# HOJA: Resumen
# =========================================================================
ws = wb.create_sheet('Resumen', 0)
title(ws, 'Handover W35 vs W34  -  Kylie MU',
      'Consensus - Final en unidades. Horizonte de foco: 2026.M09 a 2027.M04 (8 meses). '
      'W35 = CurrentWorkingView | W34 = Month-2026.M08.W34(Recovered) | LY = Consensus - Final LY M.')
ws.column_dimensions['A'].width = 4
for col, w in zip('BCDEFGH', [46, 15, 15, 15, 13, 15, 13]): ws.column_dimensions[col].width = w

put(ws, 'B4', 'HEADLINE', font=h2, border=False)
header_row(ws, 5, ['Consensus - Final (u)', 'LY', 'W34 (ciclo pasado)', 'W35 (este ciclo)',
                   'Δ vs LC (u)', 'Δ vs LC (%)', 'Δ vs LY (u)', 'Δ vs LY (%)'], start=2)
rows_head = [
    ('Horizonte 2026.M09 - 2027.M04', HC),
    ('   del cual: FY27 Q1 (Sep-26)',  f'{TRI_},"FY27 Q1",{HC}'),
    ('   del cual: FY27 Q2 (Oct-Dic 26)', f'{TRI_},"FY27 Q2",{HC}'),
    ('   del cual: FY27 Q3 (Ene-Mar 27)', f'{TRI_},"FY27 Q3",{HC}'),
    ('   del cual: FY27 Q4 (Abr-27)',  f'{TRI_},"FY27 Q4",{HC}'),
]
r = 6
for lab, crit in rows_head:
    isTot = r == 6
    put(ws, f'B{r}', lab, font=bodb if isTot else bod, fill=fill_tot if isTot else None)
    put(ws, f'C{r}', f'={sif(LYC, crit)}',  font=bodb if isTot else bod, fmt=NUM, fill=fill_tot if isTot else None)
    put(ws, f'D{r}', f'={sif(W34C, crit)}', font=bodb if isTot else bod, fmt=NUM, fill=fill_tot if isTot else None)
    put(ws, f'E{r}', f'={sif(W35C, crit)}', font=bodb if isTot else bod, fmt=NUM, fill=fill_tot if isTot else None)
    put(ws, f'F{r}', f'=E{r}-D{r}', font=bodb if isTot else bod, fmt=NUM, fill=fill_tot if isTot else None)
    put(ws, f'G{r}', f'=IFERROR(E{r}/D{r}-1,"")', font=bodb if isTot else bod, fmt=PCT, fill=fill_tot if isTot else None)
    put(ws, f'H{r}', f'=E{r}-C{r}', font=bodb if isTot else bod, fmt=NUM, fill=fill_tot if isTot else None)
    put(ws, f'I{r}', f'=IFERROR(E{r}/C{r}-1,"")', font=bodb if isTot else bod, fmt=PCT, fill=fill_tot if isTot else None)
    r += 1
ws.column_dimensions['I'].width = 13

# YoY normalizado
r = 12
put(ws, f'B{r}', 'Horizonte EXCLUYENDO 2027.M02 (mes distorsionado por el one-off de Feb-26)',
    font=bodb, fill=fill_amb)
crit_x = f'{MES_},"<>2027.M02",{HC}'
put(ws, f'C{r}', f'={sif(LYC, crit_x)}',  font=bodb, fmt=NUM, fill=fill_amb)
put(ws, f'D{r}', f'={sif(W34C, crit_x)}', font=bodb, fmt=NUM, fill=fill_amb)
put(ws, f'E{r}', f'={sif(W35C, crit_x)}', font=bodb, fmt=NUM, fill=fill_amb)
put(ws, f'F{r}', f'=E{r}-D{r}', font=bodb, fmt=NUM, fill=fill_amb)
put(ws, f'G{r}', f'=IFERROR(E{r}/D{r}-1,"")', font=bodb, fmt=PCT, fill=fill_amb)
put(ws, f'H{r}', f'=E{r}-C{r}', font=bodb, fmt=NUM, fill=fill_amb)
put(ws, f'I{r}', f'=IFERROR(E{r}/C{r}-1,"")', font=bodb, fmt=PCT, fill=fill_amb)
ws['B12'].comment = Comment(
    'LY de 2027.M02 = 2,027.M02 leido como Feb-26: 23.589 u, ~5x un mes normal.\n'
    'Concentrado en 2 EAN de brochas que hicieron pipe-fill en Feb-26:\n'
    'KJCLIP REG 9.563 u y UNVL BLSH PINCEAU04 7.265 u.\n'
    'Neutralizando ese mes, el YoY del scope pasa de -31,5% a +2,2%.', 'Analisis')

# Bridge
put(ws, 'B15', 'BRIDGE  W34 → W35  (horizonte M09-M04, unidades)', font=h2, border=False)
header_row(ws, 16, ['Concepto', 'Unidades', 'Comentario'], start=2)
ws.column_dimensions['D'].width = 15
bridge = [
    ('W34 - Consensus ciclo pasado', f'={sif(W34C, HC)}', 'Punto de partida', fill_tot, bodb),
    ('Δ System FC  (lineas que usan el sistema)',
     f'={sif(W35S, MODO_,SIS,HC)}-{sif(W34S, MODO_,SIS,HC)}',
     'El motor estadistico bajo su propio numero', None, bod),
    ('Δ Reasonability Adjustment',
     f'={sif(W35RA, MODO_,SIS,HC)}-{sif(W34RA, MODO_,SIS,HC)}',
     'Se retiraron los ajustes manuales de Dic-26 (+2.000) y Ene-27 (+1.000) y el -1.000 de Abr-27', None, bod),
    ('Δ Total Demand Assumption',
     f'={sif(W35TDA, MODO_,SIS,HC)}-{sif(W34TDA, MODO_,SIS,HC)}',
     'Se limpio el -173/mes que arrastraba TINT BRUSH PINCEAU 03', None, bod),
    ('Δ Otras capas no incluidas en la extraccion (residual)',
     (f'=({sif(W35C, MODO_,SIS,HC)}-{sif(W35S, MODO_,SIS,HC)}-{sif(W35RA, MODO_,SIS,HC)}-{sif(W35TDA, MODO_,SIS,HC)})'
      f'-({sif(W34C, MODO_,SIS,HC)}-{sif(W34S, MODO_,SIS,HC)}-{sif(W34RA, MODO_,SIS,HC)}-{sif(W34TDA, MODO_,SIS,HC)})'),
     'Consensus menos la suma de capas extraidas. Initiative / Prometheus no vienen en este extract', fill_amb, bod),
    ('Δ Lineas en modo manual (Ignore System FC = 2)',
     f'={sif(W35C, MODO_,MAN,HC)}-{sif(W34C, MODO_,MAN,HC)}',
     'Face Multi: el consensus no se movio, aunque el System FC si (ver hoja Alertas)', None, bod),
    ('W35 - Consensus este ciclo', f'={sif(W35C, HC)}', 'Punto de llegada', fill_tot, bodb),
]
r = 17
for lab, formula, note, fl, fnt in bridge:
    put(ws, f'B{r}', lab, font=fnt, fill=fl)
    put(ws, f'D{r}', formula, font=fnt, fmt=NUM, fill=fl)
    put(ws, f'E{r}', note, font=small, fill=fl)
    ws.merge_cells(f'E{r}:I{r}')
    r += 1
put(ws, f'B{r}', 'Control (debe dar 0)', font=small)
put(ws, f'D{r}', f'=D23-(D17+D18+D19+D20+D21+D22)', font=small, fmt=NUM)

# Churn
put(ws, 'B27', 'EL NETO ESCONDE EL MOVIMIENTO REAL', font=h2, border=False)
header_row(ws, 28, ['Medida', 'Unidades', 'Lectura'], start=2)
put(ws, 'B29', 'Cambio NETO del horizonte', font=bod)
put(ws, 'D29', "=E6-D6", font=bod, fmt=NUM)
put(ws, 'E29', 'Lo que ve supply en el total', font=small); ws.merge_cells('E29:I29')
put(ws, 'B30', 'Movimiento BRUTO (suma de |Δ| por mes)', font=bod)
put(ws, 'D30', "=SUMPRODUCT(ABS('Por Mes'!F6:F13))", font=bod, fmt=NUM)
put(ws, 'E30', 'Volumen que efectivamente se re-faseo entre meses', font=small); ws.merge_cells('E30:I30')
put(ws, 'B31', 'Movimiento BRUTO (suma de |Δ| por EAN x mes)', font=bod)
RES_D31 = ws['D31']
put(ws, 'E31', 'Volumen re-faseado a nivel codigo x mes', font=small); ws.merge_cells('E31:I31')
put(ws, 'B32', 'Ratio bruto / neto (por mes)', font=bodb, fill=fill_amb)
put(ws, 'D32', '=IFERROR(D30/ABS(D29),"")', font=bodb, fmt='0.0"x"', fill=fill_amb)
put(ws, 'E32', 'Por cada unidad de cambio neto se movieron ~3,6 unidades de fase', font=small, fill=fill_amb)
ws.merge_cells('E32:I32')

# Mensajes
put(ws, 'B35', 'MENSAJES PARA LA PRESENTACION', font=h2, border=False)
msgs = [
  ('Vs LC', 'El scope de brochas y accesorios de Kylie cierra el ciclo en -2,0K u / -5% sobre M09-M04. '
            'El numero total casi no se movio: lo que cambio fue la fase.'),
  ('Vs LC', 'El 100% del descenso neto viene de UN codigo: TINT BRUSH PINCEAU 03 (-2,5K u / -10%). '
            'El resto del scope suma +0,5K u.'),
  ('Vs LC', 'Se adelanto volumen a Sep-26 (+1,6K / +25%) y se saco de Oct-26 (-1,3K / -24%), '
            'Mar-27 (-1,9K / -28%) y Abr-27 (-1,2K / -32%). Q1 sube, Q3 y Q4 bajan.'),
  ('Vs LC', 'El movimiento es de sistema, no de criterio: el System FC bajo -2,1K u y ademas se retiraron '
            'todos los ajustes manuales (RA -2,0K, TDA +1,2K al limpiar el -173/mes).'),
  ('Vs LY', 'El -31,5% vs LY es un artefacto: Feb-26 cargo 23,6K u de pipe-fill de dos brochas nuevas '
            '(KJCLIP 9,6K + UNVL BLSH 7,3K). Neutralizando Feb, el scope esta en +2,2% vs LY.'),
  ('Vs LY', 'Face Multi -50% vs LY es el mismo efecto base. Accesories -22% vs LY es real y se explica '
            'por TINT BRUSH PINCEAU 03 (-6,1K u vs LY).'),
  ('Riesgo', 'UNVL BLSH PINCEAU04: el System FC subio a 11,1K u y el consensus se quedo en 6,5K por '
             'Total Demand Assumption. Gap de +4,6K u sin revisar.'),
  ('Riesgo', 'PRS SCLP CMPLN 05: el System FC se fue a 0 y el consensus termina en Mar-27. '
             'Confirmar si es descontinuacion o hueco de mantenimiento.'),
]
header_row(ws, 36, ['Bloque', 'Mensaje'], start=2)
ws.column_dimensions['B'].width = 46
r = 37
for blk, m in msgs:
    put(ws, f'B{r}', blk, font=bodb, align='center',
        fill=fill_grn if blk == 'Vs LC' else (fill_tot if blk == 'Vs LY' else fill_red))
    put(ws, f'D{r}', m, font=bod, wrap=True)
    ws.merge_cells(f'D{r}:I{r}')
    ws.row_dimensions[r].height = 30
    r += 1
ws.sheet_view.showGridLines = False

# =========================================================================
# HOJA: Por Mes
# =========================================================================
ws = wb.create_sheet('Por Mes')
title(ws, 'Consensus - Final por mes', 'Horizonte de foco sombreado. Unidades.')
header_row(ws, 4, ['Mes','Trim. FY','LY','W34','W35','Δ vs LC (u)','Δ vs LC (%)','Δ vs LY (u)','Δ vs LY (%)',
                   'W35 System FC','W34 System FC','Δ System FC'],
           widths=[12,10,12,12,12,13,12,13,12,13,13,13])
allm = sorted(d.Month.unique())
r = 5
put(ws, 'A5', 'Cerrado / en curso', font=small, border=False)
r = 6
hor_start = r
for m in HOR:
    put(ws, f'A{r}', m, font=bodb); put(ws, f'B{r}', QMAP[m], font=bod, align='center')
    c = f'{MES_},"{m}"'
    put(ws, f'C{r}', f'={sif(LYC, c)}',  fmt=NUM)
    put(ws, f'D{r}', f'={sif(W34C, c)}', fmt=NUM)
    put(ws, f'E{r}', f'={sif(W35C, c)}', fmt=NUM)
    put(ws, f'F{r}', f'=E{r}-D{r}', fmt=NUM)
    put(ws, f'G{r}', f'=IFERROR(E{r}/D{r}-1,"")', fmt=PCT)
    put(ws, f'H{r}', f'=E{r}-C{r}', fmt=NUM)
    put(ws, f'I{r}', f'=IFERROR(E{r}/C{r}-1,"")', fmt=PCT)
    put(ws, f'J{r}', f'={sif(W35S, c)}', fmt=NUM)
    put(ws, f'K{r}', f'={sif(W34S, c)}', fmt=NUM)
    put(ws, f'L{r}', f'=J{r}-K{r}', fmt=NUM)
    r += 1
tot = r
put(ws, f'A{tot}', 'TOTAL M09-M04', font=bodb, fill=fill_tot)
put(ws, f'B{tot}', '', fill=fill_tot)
for col in 'CDEJKL':
    put(ws, f'{col}{tot}', f'=SUM({col}{hor_start}:{col}{tot-1})', font=bodb, fmt=NUM, fill=fill_tot)
put(ws, f'F{tot}', f'=E{tot}-D{tot}', font=bodb, fmt=NUM, fill=fill_tot)
put(ws, f'G{tot}', f'=IFERROR(E{tot}/D{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)
put(ws, f'H{tot}', f'=E{tot}-C{tot}', font=bodb, fmt=NUM, fill=fill_tot)
put(ws, f'I{tot}', f'=IFERROR(E{tot}/C{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)

# meses fuera de horizonte, como contexto
r = tot + 2
put(ws, f'A{r}', 'Fuera del horizonte de foco (contexto)', font=h2, border=False); r += 1
header_row(ws, r, ['Mes','Trim. FY','LY','W34','W35','Δ vs LC (u)','Δ vs LC (%)','Δ vs LY (u)','Δ vs LY (%)',
                   'W35 System FC','W34 System FC','Δ System FC'])
r += 1
for m in [x for x in allm if x not in HOR]:
    put(ws, f'A{r}', m, font=bod); put(ws, f'B{r}', QMAP[m], font=bod, align='center')
    c = f'{MES_},"{m}"'
    put(ws, f'C{r}', f'={sif(LYC, c)}',  fmt=NUM); put(ws, f'D{r}', f'={sif(W34C, c)}', fmt=NUM)
    put(ws, f'E{r}', f'={sif(W35C, c)}', fmt=NUM); put(ws, f'F{r}', f'=E{r}-D{r}', fmt=NUM)
    put(ws, f'G{r}', f'=IFERROR(E{r}/D{r}-1,"")', fmt=PCT)
    put(ws, f'H{r}', f'=E{r}-C{r}', fmt=NUM); put(ws, f'I{r}', f'=IFERROR(E{r}/C{r}-1,"")', fmt=PCT)
    put(ws, f'J{r}', f'={sif(W35S, c)}', fmt=NUM); put(ws, f'K{r}', f'={sif(W34S, c)}', fmt=NUM)
    put(ws, f'L{r}', f'=J{r}-K{r}', fmt=NUM)
    r += 1
put(ws, f'A{r+1}', '2026.M07 esta cerrado (System FC = Consensus = Actuals) y 2026.M08 sigue facturando: '
                   'por eso quedan fuera del foco.', font=small, border=False)
ws.freeze_panes = 'C5'; ws.sheet_view.showGridLines = False

# =========================================================================
# HOJA: Product Lines
# =========================================================================
ws = wb.create_sheet('Product Lines')
title(ws, 'Top Product Lines  -  W35 vs W34 vs LY', 'Horizonte 2026.M09 - 2027.M04. Unidades.')
header_row(ws, 4, ['Product Line','# EAN','LY','W34','W35','% del libro W35','Δ vs LC (u)','Δ vs LC (%)',
                   'Δ vs LY (u)','Δ vs LY (%)','Δ vs LY ex-Feb27 (u)','Contribucion al Δ LC'],
           widths=[32,8,12,12,12,14,13,12,13,12,17,17])
order = (d[d.inHor].groupby('PL')['C_cons'].sum().sort_values(ascending=False).index.tolist())
r = 5; first = r
for pl in order:
    cpl = f'{PL_},"{pl}",{HC}'
    cplx = f'{PL_},"{pl}",{MES_},"<>2027.M02",{HC}'
    put(ws, f'A{r}', pl, font=bodb)
    put(ws, f'B{r}', int(d[(d.PL == pl)].EAN.nunique()), fmt='0', align='center')
    put(ws, f'C{r}', f'={sif(LYC, cpl)}',  fmt=NUM)
    put(ws, f'D{r}', f'={sif(W34C, cpl)}', fmt=NUM)
    put(ws, f'E{r}', f'={sif(W35C, cpl)}', fmt=NUM)
    put(ws, f'F{r}', f'=IFERROR(E{r}/E$99,"")', fmt=PCT)
    put(ws, f'G{r}', f'=E{r}-D{r}', fmt=NUM)
    put(ws, f'H{r}', f'=IFERROR(E{r}/D{r}-1,"")', fmt=PCT)
    put(ws, f'I{r}', f'=E{r}-C{r}', fmt=NUM)
    put(ws, f'J{r}', f'=IFERROR(E{r}/C{r}-1,"")', fmt=PCT)
    put(ws, f'K{r}', f'={sif(W35C, cplx)}-{sif(LYC, cplx)}', fmt=NUM)
    put(ws, f'L{r}', f'=IFERROR(G{r}/$G$99,"")', fmt=PCT)
    r += 1
last = r - 1
tot = r
put(ws, f'A{tot}', 'TOTAL', font=bodb, fill=fill_tot)
for col in 'BCDEGIK':
    put(ws, f'{col}{tot}', f'=SUM({col}{first}:{col}{last})', font=bodb, fmt=(NUM if col != 'B' else '0'), fill=fill_tot)
put(ws, f'F{tot}', f'=IFERROR(E{tot}/E$99,"")', font=bodb, fmt=PCT, fill=fill_tot)
put(ws, f'H{tot}', f'=IFERROR(E{tot}/D{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)
put(ws, f'J{tot}', f'=IFERROR(E{tot}/C{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)
put(ws, f'L{tot}', f'=IFERROR(G{tot}/$G$99,"")', font=bodb, fmt=PCT, fill=fill_tot)
# anclas para los % (fila 99, oculta)
put(ws, 'A99', 'Anclas de calculo (no borrar)', font=small, border=False)
put(ws, 'E99', f'={sif(W35C, HC)}', font=small, fmt=NUM)
put(ws, 'G99', f'={sif(W35C, HC)}-{sif(W34C, HC)}', font=small, fmt=NUM)

# detalle mensual por product line
r = tot + 2
put(ws, f'A{r}', 'Detalle mensual por Product Line  -  Δ vs LC (u)', font=h2, border=False); r += 1
header_row(ws, r, ['Product Line'] + HOR + ['Total'], widths=[32] + [12]*9)
mfirst = r + 1; rr = r + 1
for pl in order:
    put(ws, f'A{rr}', pl, font=bod)
    for i, m in enumerate(HOR):
        col = get_column_letter(2 + i)
        c = f'{PL_},"{pl}",{MES_},"{m}"'
        put(ws, f'{col}{rr}', f'={sif(W35C, c)}-{sif(W34C, c)}', fmt=NUM)
    put(ws, f'J{rr}', f'=SUM(B{rr}:I{rr})', font=bodb, fmt=NUM)
    rr += 1
put(ws, f'A{rr}', 'TOTAL', font=bodb, fill=fill_tot)
for i in range(9):
    col = get_column_letter(2 + i)
    put(ws, f'{col}{rr}', f'=SUM({col}{mfirst}:{col}{rr-1})', font=bodb, fmt=NUM, fill=fill_tot)

rr += 2
put(ws, f'A{rr}', 'Detalle mensual por Product Line  -  Consensus W35 (u)', font=h2, border=False); rr += 1
header_row(ws, rr, ['Product Line'] + HOR + ['Total'])
f2 = rr + 1; rr += 1
for pl in order:
    put(ws, f'A{rr}', pl, font=bod)
    for i, m in enumerate(HOR):
        col = get_column_letter(2 + i)
        crit = PL_ + ',"' + pl + '",' + MES_ + ',"' + m + '"'
        put(ws, f'{col}{rr}', '=' + sif(W35C, crit), fmt=NUM)
    put(ws, f'J{rr}', f'=SUM(B{rr}:I{rr})', font=bodb, fmt=NUM)
    rr += 1
put(ws, f'A{rr}', 'TOTAL', font=bodb, fill=fill_tot)
for i in range(9):
    col = get_column_letter(2 + i)
    put(ws, f'{col}{rr}', f'=SUM({col}{f2}:{col}{rr-1})', font=bodb, fmt=NUM, fill=fill_tot)
ws.sheet_view.showGridLines = False

# =========================================================================
# HOJA: Detalle EAN
# =========================================================================
ws = wb.create_sheet('Detalle EAN')
title(ws, 'Detalle por EAN  -  ordenado por magnitud del cambio vs ciclo pasado',
      'Horizonte 2026.M09 - 2027.M04. Unidades. "Otras capas" = Consensus menos (System FC + Reasonability Adj + Total Demand Assumption).')
header_row(ws, 4, ['Product Line','EAN','Planning Item Description','Modo','LY','W34','W35',
                   'Δ vs LC (u)','Δ vs LC (%)','Δ vs LY (u)','Δ vs LY (%)',
                   'Δ System FC','Δ Reason. Adj','Δ Total Dem. Assum.','Δ Otras capas',
                   'W35 System FC','Gap SysFC vs Consensus'],
           widths=[28,16,40,10,11,11,11,12,11,12,11,13,13,15,13,13,15])
r = 5; first = r
for _, e in EANS.iterrows():
    ce = f'{EAN_},"{e.EAN}",{HC}'
    put(ws, f'A{r}', e.PL, font=bod)
    put(ws, f'B{r}', e.EAN, font=bod, align='center')
    put(ws, f'C{r}', e.Desc, font=bod)
    put(ws, f'D{r}', d.loc[d.EAN == e.EAN, 'Modo'].iloc[0], font=bod, align='center')
    put(ws, f'E{r}', f'={sif(LYC, ce)}',  fmt=NUM)
    put(ws, f'F{r}', f'={sif(W34C, ce)}', fmt=NUM)
    put(ws, f'G{r}', f'={sif(W35C, ce)}', fmt=NUM)
    put(ws, f'H{r}', f'=G{r}-F{r}', font=bodb, fmt=NUM)
    put(ws, f'I{r}', f'=IFERROR(G{r}/F{r}-1,"")', fmt=PCT)
    put(ws, f'J{r}', f'=G{r}-E{r}', fmt=NUM)
    put(ws, f'K{r}', f'=IFERROR(G{r}/E{r}-1,"")', fmt=PCT)
    put(ws, f'L{r}', f'={sif(W35S, ce)}-{sif(W34S, ce)}', fmt=NUM)
    put(ws, f'M{r}', f'={sif(W35RA, ce)}-{sif(W34RA, ce)}', fmt=NUM)
    put(ws, f'N{r}', f'={sif(W35TDA, ce)}-{sif(W34TDA, ce)}', fmt=NUM)
    put(ws, f'O{r}', f'=H{r}-L{r}-M{r}-N{r}', fmt=NUM)
    put(ws, f'P{r}', f'={sif(W35S, ce)}', fmt=NUM)
    put(ws, f'Q{r}', f'=P{r}-G{r}', fmt=NUM)
    r += 1
tot = r
put(ws, f'A{tot}', 'TOTAL', font=bodb, fill=fill_tot)
for col in 'BCD': put(ws, f'{col}{tot}', '', fill=fill_tot)
for col in 'EFGHJLMNOPQ':
    put(ws, f'{col}{tot}', f'=SUM({col}{first}:{col}{tot-1})', font=bodb, fmt=NUM, fill=fill_tot)
put(ws, f'I{tot}', f'=IFERROR(G{tot}/F{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)
put(ws, f'K{tot}', f'=IFERROR(G{tot}/E{tot}-1,"")', font=bodb, fmt=PCT, fill=fill_tot)
ws['O4'].comment = Comment(
    'La extraccion no trae Initiative Forecast ni Prometheus Fcst Consensus.\n'
    'Esta columna es el remanente entre el Consensus - Final y la suma de las capas que si vienen.\n'
    'Es consistente con el gap documentado en CONTEXTO-DATOS.md seccion 6.', 'Analisis')
ws['D4'].comment = Comment(
    'Manual = Ignore System Forecast Flag = 2: el consensus NO toma el System FC.\n'
    'En esas lineas un movimiento del System FC no llega al numero comprometido.', 'Analisis')
ws.freeze_panes = 'E5'; ws.sheet_view.showGridLines = False

# =========================================================================
# HOJA: EAN x Mes
# =========================================================================
ws = wb.create_sheet('EAN x Mes')
title(ws, 'Matriz EAN x Mes', 'Consensus - Final en unidades. Horizonte 2026.M09 - 2027.M04.')
MTX = {}
def matrix(startrow, label, kind):
    put(ws, f'A{startrow}', label, font=h2, border=False)
    header_row(ws, startrow + 1, ['EAN', 'Planning Item Description'] + HOR + ['Total'],
               widths=[16, 40] + [11]*9)
    rr = startrow + 2; f0 = rr
    for _, e in EANS.iterrows():
        put(ws, f'A{rr}', e.EAN, font=bod, align='center')
        put(ws, f'B{rr}', e.Desc, font=bod)
        for i, m in enumerate(HOR):
            col = get_column_letter(3 + i)
            c = f'{EAN_},"{e.EAN}",{MES_},"{m}"'
            if kind == 'W35':   f = f'={sif(W35C, c)}'
            elif kind == 'W34': f = f'={sif(W34C, c)}'
            elif kind == 'LY':  f = f'={sif(LYC, c)}'
            else:               f = f'={sif(W35C, c)}-{sif(W34C, c)}'
            put(ws, f'{col}{rr}', f, fmt=NUM)
        put(ws, f'K{rr}', f'=SUM(C{rr}:J{rr})', font=bodb, fmt=NUM)
        rr += 1
    put(ws, f'A{rr}', 'TOTAL', font=bodb, fill=fill_tot); put(ws, f'B{rr}', '', fill=fill_tot)
    for i in range(9):
        col = get_column_letter(3 + i)
        put(ws, f'{col}{rr}', f'=SUM({col}{f0}:{col}{rr-1})', font=bodb, fmt=NUM, fill=fill_tot)
    MTX[kind] = (f0, rr - 1)
    return rr + 3

nr = matrix(4,  'A. Δ vs ciclo pasado  (W35 - W34)', 'D')
nr = matrix(nr, 'B. Consensus W35 (este ciclo)', 'W35')
nr = matrix(nr, 'C. Consensus W34 (ciclo pasado)', 'W34')
nr = matrix(nr, 'D. Consensus - Final LY M (ano pasado)', 'LY')
ws.freeze_panes = 'C5'; ws.sheet_view.showGridLines = False

# rangos reales del bloque de deltas de la matriz EAN x Mes
DF0, DF1 = MTX['D']
RES_D31.value = f"=SUMPRODUCT(ABS('EAN x Mes'!C{DF0}:J{DF1}))"
RES_D31.font = bod; RES_D31.number_format = NUM; RES_D31.border = box
ROW_117254 = DF0 + list(EANS.EAN).index('4064941117254')

# =========================================================================
# HOJA: Alertas
# =========================================================================
ws = wb.create_sheet('Alertas')
title(ws, 'Alertas y puntos a revisar', 'Ordenadas por impacto en unidades sobre el horizonte M09-M04.')
header_row(ws, 4, ['#','Prioridad','EAN','Codigo','Hallazgo','Impacto (u)','Accion sugerida'],
           widths=[5,11,16,38,64,13,58])
alerts = [
    ('Alta', '4064941192046', 'KJ MU FACE ML UNVL BLSH PINCEAU04 IV',
     'El System FC subio de 4.233 a 11.105 u (+162%) pero la linea esta en Ignore System FC = 2, '
     'asi que el consensus se quedo clavado en 6.500 u de Total Demand Assumption. El sistema ve 4,6K u mas de las que comprometemos.',
     '=P5', 'Revisar si el TDA de 6.500 sigue vigente o si hay que soltar el System FC. Es el mayor upside sin capturar del scope.'),
    ('Alta', '4064941161349', 'KJ MU OTH ACC TINT BRUSH PINCEAU 03 IV',
     'Unico driver del descenso neto del ciclo: -2.508 u (-10%). Ademas se re-faseo fuerte dentro del horizonte '
     '(Sep +864, Oct -962, Mar -1.905, Abr -1.223). Se retiraron todos los ajustes manuales (RA +2.000 Dic/Ene, TDA -173/mes).',
     '=P6', 'Confirmar que la limpieza de capas fue intencional. Este codigo solo es el 55% del libro y el 123% del descenso neto del ciclo.'),
    ('Media', '4064941192060', 'KJ MU FACE ML BRUSH PRS SCLP CMPLN 05 IV',
     'El System FC se fue de 5.777 u a 0 en todo el horizonte. El consensus no se movio (linea manual) '
     'pero termina en 2027.M03: no hay numero de Abr-27 en adelante, y LY si tenia 320 u en Abr.',
     '=P7', 'Confirmar si es descontinuacion (correcto) o hueco de mantenimiento (hay que extender el forecast).'),
    ('Media', '4064941117254', 'KJ MU OTH ACC BRUSH CONCE BRUSH IV',
     'Neto casi plano (+342 u) pero con el mayor re-faseo relativo del scope: Sep +544, Dic +542, Oct -277, Feb -1.007.',
     '=P8', 'Validar con el cliente el timing de Feb-27: es la caida mas grande y no tiene ajuste manual detras.'),
    ('Media', '4064941200116', 'KJ MU FACE ML BRUSH KJCLIP REG IV',
     'El System FC cayo de 1.706 a 29 u. Sin impacto en consensus (linea manual, TDA -4.500 y capa residual +5.886). '
     'YoY -85% por el pipe-fill de 9.563 u en Feb-26.',
     '=P9', 'La estructura de capas de este codigo es ilegible: TDA negativo grande compensado por una capa que no viene en el extract. Pedir el desglose completo.'),
    ('Baja', '4064941039662', 'KJ MU OTH ACC BRUSH n/a BROW FY21 IV',
     'Unico EAN de la product line Kylie Eye Brushes. Consensus = 0 en W34 y en W35, pero LY tenia 139 u en el horizonte. '
     'No hay System FC ni capas manuales.',
     '=P10', 'Confirmar descontinuacion y sacar la product line del scope, o levantar el forecast si sigue viva.'),
    ('Metodo', '-', 'Todo el scope',
     'La comparacion vs LY del total (-31,5%) esta dominada por Feb-26: 23.589 u contra ~5K de un mes normal, '
     'con 16,8K u en dos brochas que hicieron pipe-fill. Sin ese mes el scope esta en +2,2% vs LY.',
     '=P11', 'Presentar el YoY siempre ex-Feb, o marcar Feb-26 como excepcion en la lamina. Si no, la conclusion es falsa.'),
    ('Metodo', '-', 'Todo el scope',
     'El Consensus - Final no cuadra con la suma de capas extraidas: faltan Initiative Forecast y Prometheus Fcst Consensus. '
     'El residual explica +1.461 u del delta del ciclo.',
     '=P12', 'Pedir a O9 el extract con todas las capas para poder atribuir el cambio al 100%.'),
]
# valores de impacto calculados en columna auxiliar P (oculta)
def q(e):
    return '"' + e + '"'
impacts = {
 '4064941192046': '=' + sif(W35S, EAN_, q('4064941192046'), HC) + '-' + sif(W35C, EAN_, q('4064941192046'), HC),
 '4064941161349': '=' + sif(W35C, EAN_, q('4064941161349'), HC) + '-' + sif(W34C, EAN_, q('4064941161349'), HC),
 '4064941192060': '=' + sif(W35S, EAN_, q('4064941192060'), HC) + '-' + sif(W34S, EAN_, q('4064941192060'), HC),
 '4064941117254': 'PLACEHOLDER_117254',
 '4064941200116': '=' + sif(W35S, EAN_, q('4064941200116'), HC) + '-' + sif(W34S, EAN_, q('4064941200116'), HC),
 '4064941039662': '=-' + sif(LYC, EAN_, q('4064941039662'), HC),
 'LY':            '=' + sif(W35C, HC) + '-' + sif(LYC, HC),
 'RES':           ('=(' + sif(W35C, MODO_, SIS, HC) + '-' + sif(W35S, MODO_, SIS, HC) + '-' + sif(W35RA, MODO_, SIS, HC) + '-' + sif(W35TDA, MODO_, SIS, HC) + ')'
                   + '-(' + sif(W34C, MODO_, SIS, HC) + '-' + sif(W34S, MODO_, SIS, HC) + '-' + sif(W34RA, MODO_, SIS, HC) + '-' + sif(W34TDA, MODO_, SIS, HC) + ')'),
}
keys = ['4064941192046','4064941161349','4064941192060','4064941117254','4064941200116','4064941039662','LY','RES']
r = 5
for i, (prio, ean, code, find, imp, act) in enumerate(alerts, start=1):
    fl = fill_red if prio == 'Alta' else (fill_amb if prio == 'Media' else (fill_grn if prio == 'Baja' else None))
    put(ws, f'A{r}', i, font=bodb, align='center')
    put(ws, f'B{r}', prio, font=bodb, align='center', fill=fl)
    put(ws, f'C{r}', ean, font=bod, align='center')
    put(ws, f'D{r}', code, font=bod)
    put(ws, f'E{r}', find, font=bod, wrap=True)
    put(ws, f'F{r}', imp, font=bodb, fmt=NUM)
    put(ws, f'G{r}', act, font=bod, wrap=True)
    _f = impacts[keys[i-1]]
    if _f == 'PLACEHOLDER_117254':
        _f = f"=SUMPRODUCT(ABS('EAN x Mes'!C{ROW_117254}:J{ROW_117254}))"
    put(ws, f'P{r}', _f, font=small, fmt=NUM, border=False)
    ws.row_dimensions[r].height = 58
    r += 1
put(ws, f'A{r+1}', 'Columna P: celdas auxiliares que alimentan "Impacto (u)". No borrar.', font=small, border=False)
put(ws, f'A{r+2}', 'Impacto (u): fila 1 = gap System FC vs consensus; fila 2 = delta de consensus vs ciclo pasado; '
                   'filas 3 y 5 = delta de System FC; fila 4 = movimiento bruto entre meses; fila 6 = volumen LY sin forecast; '
                   'fila 7 = delta vs LY del scope; fila 8 = parte del delta del ciclo que no explican las capas extraidas.', font=small, border=False)
ws.sheet_view.showGridLines = False

# =========================================================================
# HOJA: Notas
# =========================================================================
ws = wb.create_sheet('Notas')
title(ws, 'Alcance, metodo y advertencias')
ws.column_dimensions['A'].width = 3
ws.column_dimensions['B'].width = 34
ws.column_dimensions['C'].width = 110
notes = [
 ('ALCANCE DEL ARCHIVO', ''),
 ('Que trae el extract',
  'handover W35.xlsx contiene 3 product lines y 8 EAN, todos brochas y accesorios de Kylie MU: '
  'Accesories (00006010), Face Multi (00006011) y Kylie Eye Brushes (00006121). 93 filas EAN x mes.'),
 ('ADVERTENCIA - lee esto primero',
  'Este NO es el scope completo de la casa Kylie. No hay Skin Tint, ni Lip, ni el resto del maquillaje: '
  'solo el bloque de brochas y accesorios, 38,7K u en el horizonte. Todo lo que dice este workbook es cierto '
  'para ese bloque y no se puede extrapolar a Kylie MU total. Para la presentacion hace falta re-exportar '
  'el handover sin filtro de product line (misma plantilla de dos vistas + Consensus - Final LY M).'),
 ('Reproducible',
  'analysis/handover_w35/build_workbook.py regenera este archivo. Basta con reemplazar handover W35.xlsx '
  'por el extract completo y volver a correrlo: todas las hojas escalan solas.'),
 ('', ''),
 ('DEFINICIONES', ''),
 ('W35 / este ciclo', 'Bloque de columnas con fila A = CurrentWorkingView.'),
 ('W34 / ciclo pasado', 'Bloque de columnas con fila A = Month-2026.M08.W34(Recovered).'),
 ('LY', 'Medida Consensus - Final LY M. Como O9 sobreescribe la historia al cerrar el mes, en meses cerrados '
        'esa medida equivale al actual del ano pasado.'),
 ('Horizonte de foco', '2026.M09 a 2027.M04, 8 meses, segun lo pedido. El extract cubre 2026.M07 a 2027.M06; '
                       'M07 esta cerrado y M08 sigue facturando, por eso quedan fuera (hoja Por Mes los muestra como contexto).'),
 ('Unidades', 'Todo el workbook esta en unidades. El extract no trae valor.'),
 ('Modo forecast', 'Ignore System Forecast Flag = 2 significa que el consensus NO toma el System FC. '
                   '3 de los 8 EAN estan asi (toda la product line Face Multi, 24% del libro). '
                   'En esas lineas el System FC puede moverse muchisimo sin que el numero comprometido cambie.'),
 ('Otras capas / residual',
  'El extract trae System FC, Reasonability Adjustment y Total Demand Assumption, pero no Initiative Forecast '
  'ni Prometheus Fcst Consensus. Por eso el Consensus - Final no cuadra con la suma de capas y aparece un residual. '
  'Es el mismo gap documentado en CONTEXTO-DATOS.md seccion 6.'),
 ('', ''),
 ('COMO LEER LOS NUMEROS', ''),
 ('Delta vs LC', 'W35 menos W34. Positivo = subimos el compromiso a supply respecto del ciclo pasado.'),
 ('Delta vs LY', 'W35 menos Consensus - Final LY M. Ojo con 2027.M02: ver la siguiente nota.'),
 ('El one-off de Feb-26',
  'LY de 2027.M02 vale 23.589 u contra ~5K de un mes normal. Son dos brochas que hicieron pipe-fill en Feb-26: '
  'KJCLIP REG 9.563 u y UNVL BLSH PINCEAU04 7.265 u. Ese unico mes convierte un scope que esta en +2,2% vs LY '
  'en un -31,5%. Presentar siempre el YoY ex-Feb, o marcar el mes como excepcion.'),
 ('Neto vs bruto',
  'El cambio neto del ciclo son -2.039 u, pero el movimiento bruto entre meses son 7.429 u (3,6x) y a nivel '
  'EAN x mes son 9.163 u. El mensaje no es "bajamos 5%", es "re-faseamos el libro".'),
 ('No se puede medir accuracy',
  'Con estos datos no se puede calcular MAPE ni BIAS: O9 sobreescribe el forecast con el actual al cerrar el mes. '
  'Haria falta el extract con fotos a lag-1 y lag-3.'),
 ('', ''),
 ('FUENTE', ''),
 ('Archivo', 'handover W35.xlsx (repo germanach96/DP), extraccion O9, hoja Sheet1.'),
 ('Contexto de negocio', 'CONTEXTO-DATOS.md (repo germanach96/DP).'),
 ('Trimestres fiscales', 'FY de julio a junio. FY27 Q1 = Jul-Sep 26, Q2 = Oct-Dic 26, Q3 = Ene-Mar 27, Q4 = Abr-Jun 27. '
                         'Dentro del horizonte, Q1 solo aporta Sep y Q4 solo aporta Abr.'),
]
r = 4
for k, v in notes:
    if v == '':
        if k: put(ws, f'B{r}', k, font=h2, border=False)
        r += 1; continue
    put(ws, f'B{r}', k, font=bodb, wrap=True)
    put(ws, f'C{r}', v, font=bod, wrap=True)
    ws.row_dimensions[r].height = max(15, 13 * (len(v) // 105 + 1))
    if k.startswith('ADVERTENCIA'):
        ws[f'B{r}'].fill = fill_red; ws[f'C{r}'].fill = fill_red
    r += 1
ws.sheet_view.showGridLines = False

for s in wb.worksheets:
    s.sheet_properties.tabColor = NAVY

wb.move_sheet('Datos', offset=len(wb.sheetnames))
wb.save(OUT)
print('escrito:', OUT)
