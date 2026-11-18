# Smart Cleaner

A web app that prepares any tabular dataset (CSV or Excel) for Machine Learning. It profiles every column, finds anomalies, recommends a cleaning step with a numeric justification, applies your choices without data leakage, and exports the cleaned data with a per-feature Excel report.

It is generic: nothing is tied to one dataset. The tests run the full flow on iris, wine, diabetes and a multi-sheet Excel file.

## Workflow

1. **Import:** upload a CSV (`,` or `;` separator, European decimals supported) or an Excel file and pick the sheet. Choose supervised (with a target column) or unsupervised. You can correct the inferred column types.
2. **EDA:** types, statistics, missing values, outliers, distributions and a correlation heatmap, all computed on the training split.
3. **Preprocessing:** each column shows its anomalies, the recommended transformation with its reason, and every alternative with its trade-off. Accept it, pick another, or choose "none". A before/after preview is available per column.
4. **Export:** apply the choices and download a zip.

## Setup

Requirements: Python 3.12 and Node 24.

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # on macOS/Linux: .venv/bin/python

# frontend
cd ../frontend
npm install
```

## Running

Start both, then open http://localhost:5173.

```bash
# backend, from backend/ (API docs at http://localhost:8000/docs)
.venv/Scripts/python -m uvicorn app.main:app --reload

# frontend, from frontend/
npm run dev
```

If the repo sits in a OneDrive folder, `--reload` can miss edits. Restart the backend by hand after changing it.

## Tests

```bash
# backend, from backend/
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pytest tests/test_rules_missing.py::test_skewed_numeric_gets_median -q   # one test

# frontend, from frontend/
npm test
```

## How recommendations work

- **No leakage.** Exact duplicate rows (and, in supervised mode, rows without a target) are removed first. The data is then split 80/20 with a fixed seed (`random_state=42`), stratified for classification. Every statistic and every fitted transformer (imputation values, outlier fences, encoders, scalers) comes from the training split only. The test split is only transformed.
- **Reproducible.** The same file with the same mode and target always gives the same split and the same numbers. Changing the mode, the target or the order of the rows in the file changes which rows land in train.
- **Fixed, defended thresholds.** Each rule (constant, ID-like, missing, outliers, skewness, encoding, scaling, correlation, imbalance, free text, dates) uses a plain threshold with a one-sentence justification. See [§8 of the design](docs/superpowers/specs/2026-11-17-smart-cleaner-design.md#8-rules-and-thresholds-one-sentence-defence-each).
- **Never crashes on a column.** If a rule fails on an unusual column, the column gets an "analysis failed" finding and is left unchanged.

## Export contents

The zip contains:

- `train.csv` and `test.csv`: the transformed splits. The target column is never transformed.
- `report.xlsx`, with three sheets:
  - **Dataset:** the file, mode, split and dataset-level findings.
  - **Features:** one row per column, with its statistics, anomalies, the recommendation and the transformation actually applied.
  - **Correlations:** highly correlated pairs.
