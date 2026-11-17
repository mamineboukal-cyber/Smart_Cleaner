# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The backend (FastAPI) is built; the frontend is not yet. The source of truth for requirements is [docs/spec.md](docs/spec.md) (in French), refined in [docs/superpowers/specs/](docs/superpowers/specs/). Read them before you design or build anything.

## Commands (backend, run from `backend/`)

- Tests: `.venv/Scripts/python -m pytest -q`
- Dev server: `.venv/Scripts/python -m uvicorn app.main:app --reload` (API docs at http://localhost:8000/docs)
- Install deps: `.venv/Scripts/python -m pip install -r requirements.txt`

All user-facing text lives in `backend/app/i18n.py`; never hardcode strings elsewhere.

## What is being built

A generic web app for preprocessing and cleaning datasets before Machine Learning. It is a coursework project (TP).

- **Frontend:** React.js
- **Backend:** Python + FastAPI, using Pandas and scikit-learn

The workflow the spec requires:

1. **Import & configure:** upload a CSV or Excel file, choose supervised or unsupervised learning, and pick the target column if supervised.
2. **EDA tab:** show each feature's type, stats, distributions, missing values, duplicates, outliers and correlations, with interactive charts.
3. **Preprocessing tab:** for each feature, show the anomalies found and a recommended transformation with a statistical justification. Options include imputation, encoding, scaling, dropping and outlier handling. The user can accept the recommendation, choose another one, or apply nothing. Show a before/after preview.
4. **Execute & export:** apply the chosen transformations, download the transformed dataset, and generate an Excel report per feature. The report lists stats, anomalies, recommendations and the transformations actually applied.

## Key constraints

- **Generic, not dataset-specific.** The demo uses a bank-fraud dataset, but the app must also be checked on a second dataset. Don't hardcode column names or assumptions from any one dataset.
- **Prevent data leakage.** Fit transformers (imputers, scalers, encoders) on the training split only, then apply them to the other splits. Don't compute statistics on the full dataset before splitting.
- **Keep two records per feature:** what was *recommended* and what was *actually applied*. The Excel report needs both.

## Repo conventions

- `data/` is gitignored and is where local datasets go. Never commit datasets.
- `.venv/`, `node_modules/` and `.env` are also gitignored.
- The default branch for PRs is `main`. Local work currently happens on `master`.
