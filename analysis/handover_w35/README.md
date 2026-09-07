# Handover W35 vs W34 — Kylie MU

Compara el ciclo actual (`CurrentWorkingView` = W35) contra el anterior
(`Month-2026.M08.W34(Recovered)`) y contra `Consensus - Final LY M`, con foco en
**2026.M09 – 2027.M04**.

## Cómo correrlo

```bash
python3 analysis/handover_w35/build_workbook.py
python3 <ruta-skill-xlsx>/scripts/recalc.py "Handover W35 vs W34 - Kylie MU.xlsx" 280
```

Salida: `Handover W35 vs W34 - Kylie MU.xlsx` en la raíz del repo.

- `prep.py` — carga y normaliza `handover W35.xlsx` (20 columnas: 4 de jerarquía +
  8 medidas W35 + 8 medidas W34).
- `build_workbook.py` — escribe el workbook. Todas las celdas de cálculo son
  fórmulas `SUMIFS` contra la hoja `Datos`, así que el archivo se recalcula solo
  si cambia el extract.

## Advertencia de alcance

El extract actual trae **solo 3 product lines y 8 EAN** (brochas y accesorios de
Kylie MU): Accesories (00006010), Face Multi (00006011), Kylie Eye Brushes
(00006121). No es la casa Kylie completa. Para la presentación hace falta
re-exportar el handover sin filtro de product line, manteniendo las dos vistas y
la medida `Consensus - Final LY M`. Con el extract completo basta con volver a
correr el script: todas las hojas escalan solas.

## Hallazgos principales (sobre el bloque disponible)

| | LY | W34 | W35 | Δ LC | Δ LY |
|---|---|---|---|---|---|
| M09–M04 | 56.438 | 40.721 | 38.682 | −2.039 (−5,0%) | −17.756 (−31,5%) |
| M09–M04 ex-2027.M02 | 32.849 | 35.291 | 33.568 | −1.723 (−4,9%) | +719 (+2,2%) |

- El −31,5% vs LY es un artefacto de Feb-26 (23.589 u de pipe-fill, 16,8 K en dos
  brochas). Ex-Feb el scope está en **+2,2% vs LY**.
- El cambio neto del ciclo (−2.039 u) esconde 7.429 u de movimiento bruto entre
  meses (3,6x) y 9.163 u a nivel EAN × mes: el ciclo **re-faseó**, no recortó.
- El 100% del descenso neto es un solo código: TINT BRUSH PINCEAU 03 (−2.508 u).
- UNVL BLSH PINCEAU04 tiene el System FC en 11,1 K y el consensus clavado en
  6,5 K por `Ignore System Forecast Flag = 2`: gap de 4.610 u sin revisar.
