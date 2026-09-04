# O9 Scope Analysis

`Scope Analysis Report.pdf` is the deliverable. Everything here reproduces it from
`scope analysis.xlsx`.

## Reproduce

```
pip install pandas openpyxl matplotlib reportlab pillow
python3 analysis/scripts/a1_seasonality.py
python3 analysis/scripts/a2_epos.py
python3 analysis/scripts/a3_launch.py
python3 analysis/scripts/a4_layers_cuts.py
python3 analysis/scripts/a5_watchlist.py
python3 analysis/scripts/a6_archetypes.py
python3 analysis/scripts/a7_cfg_house.py
python3 analysis/scripts/charts.py
python3 analysis/scripts/report.py
```

## Layout

| Path | What it is |
|---|---|
| `scripts/load.py` | Shared loader; holds the analysis conventions below |
| `scripts/a1..a7` | Analyses; each writes JSON/CSV to `out/` |
| `scripts/viz.py` | Chart toolkit (validated dataviz palette, light surface) |
| `scripts/charts.py` | Renders the 18 figures into `charts/` |
| `scripts/pdfkit.py` | Page layout primitives |
| `scripts/report.py` | Assembles the PDF |
| `out/` | Intermediate results, including the watchlist CSVs |

## Conventions

- **Closed history is 2023.M08 to 2026.M07.** 2026.M08 is still invoicing and
  2026.M09 is in flight, so both are excluded from every calculation.
- **No accuracy metrics.** O9 overwrites history: in every closed month
  `System FC - Final` = `Consensus - Final` = `Actuals`, so the extract holds no
  pre-actual forecast and MAPE/BIAS cannot be computed. See Section 1 of the report.
- **`Gucci Fragrance Multiline (00003484)` is excluded from all aggregates**
  (37% of volume, catch-all line) and covered in Appendix A.
- **EPOS is a trend signal, not a level.** It covers a median 52% of sell-in on the
  lines that carry it, so it is only ever compared as an index or a growth rate.
- **Launch** = first actual on or after 2023.M09; 2023.M08 is the start of history,
  not a launch date.
- **Demand lost** = `cuts / (actuals + cuts)`.
