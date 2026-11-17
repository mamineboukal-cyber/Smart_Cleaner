# Smart Cleaner — Design

Date: 2026-11-17 · Status: draft for approval · Source requirements: [docs/spec.md](../../spec.md)

## 1. Intent

This is a coursework project (TP), built solo, with a **two-day deadline**. It is a generic web app that takes any CSV or Excel dataset, analyses it, recommends a cleaning step for each column, applies the user's choices without data leakage, and exports the cleaned data together with an Excel report.

**What the instructor grades:**

1. A live demo on a bank-fraud dataset
2. A validation run on a second dataset
3. The transformed dataset
4. The Excel report
5. Documented code

**The instructor's key requirement:** every column gets a recommendation backed by numeric statistical evidence, plus the full list of alternatives.

## 2. Goals, non-goals, anti-goals

**Goals**
- Every column shows three things: its numeric stats, a recommendation with a reason that quotes those numbers, and every alternative with a one-line trade-off.
- The user can accept the recommendation, pick an alternative, or choose "none" for each column, and see a before/after preview.
- No leakage. The data is split before anything is fitted, every transformer is fitted on train only, and test is only transformed.
- Output is a zip containing `train.csv`, `test.csv` and `report.xlsx`.
- The same code works on any tabular dataset, with no column names hardcoded.

**Non-goals**
- Login, a database, persistence across server restarts, multiple users at once.
- Model training. The app recommends class weights but does not train anything.
- Resampling: **no SMOTE**, no over- or under-sampling.
- Exporting a fitted pipeline (`.pkl`).
- Visual polish beyond clean and readable.

**Anti-goals** (failure even if it technically works)
- A recommendation without numbers, or a column that has no alternatives listed.
- The screen, the preview and the Excel report giving different numbers for the same column.
- Any statistic used to transform the test set being computed on test or on the full dataset.
- Rules the user can't explain out loud in one sentence.

## 3. Constraints

- Stack (fixed by the spec): React frontend, Python/FastAPI backend, Pandas, scikit-learn.
- Two days, one person. Scope is cut to what is graded.
- The typical fraud dataset (Kaggle `creditcard.csv`) has about 285k rows and 31 numeric columns, so charts must be computed on the backend and scatter plots must use sampled rows.
- Datasets live in `data/`, which is gitignored.

## 4. Approaches considered

| Approach | Trade-off | Verdict |
|---|---|---|
| **Backend computes everything, React displays it** | The backend owns all statistics, rules and chart data; React only renders. One rule engine feeds the UI and the report. | **Chosen.** |
| Ship the raw data to the browser and compute there | Freezes the page on 285k rows. | Rejected. |
| Server renders charts as images (matplotlib) | Simpler, but the spec asks for *interactive* charts. | Rejected. |
| Streamlit or a single Python app | Fastest to build, but the spec requires React. | Rejected. |

Choices about the train/test split and export:

| Option | Verdict |
|---|---|
| **A. Split inside the app, fit on train, export a zip with train, test and report** | **Chosen by the user.** It visibly proves leakage was handled. |
| B. A single cleaned file with no split | Rejected: the spec explicitly mentions leakage. |
| C. Option A plus a `.pkl` pipeline export | Rejected: not enough time. |

## 5. Decisions made by the user

- **Split:** inside the app, 80/20.
  - Supervised with a classification target: **stratified** on the target.
  - Unsupervised: **plain random split**, because there is no target.
- **Imbalance:** report the class ratio and **recommend class weights only** (`class_weight="balanced"`). The app does not resample. This is a recommendation recorded in the UI and the report, not a transformation.
- **Rule thresholds** are plain and fixed, and each one is defended in one sentence (§8).
- **The instructor may bring an unknown dataset.** Harden only these:
  - **Regression and multiclass targets.** Covered in §6 and in rules 6 and 12.
  - **Multi-sheet Excel files.** `/upload` returns the sheet names and the user picks one (the first sheet by default).
  - **Text and date columns are flagged, never crashed on.** See rule 13 and the "Never crash" note in §8.

  No other hardening is in scope.
- **Language:** every UI label, reason, trade-off line and report header comes from **one translations file**, so nothing user-facing is hardcoded. The display language is still to be confirmed (French or English).

## 6. Architecture (my calls, open to correction)

```
frontend/  (Vite + React + react-plotly.js)
  Import tab -> EDA tab -> Preprocessing tab -> Export tab
backend/   (FastAPI)
  app/main.py         routes
  app/session.py      in-memory store: session_id -> {raw df, config, split, profiles, choices}
  app/profiling.py    per-column statistics + chart data (histogram bins, box quartiles, value counts, correlation matrix)
  app/rules/          one module per rule; each returns a Finding
  app/pipeline.py     builds and fits the transformers from the user's choices, on train only
  app/report.py       Excel report (openpyxl)
  tests/              pytest for the rules and the pipeline
```

**The shared structure.** Every rule returns a `Finding`, and the EDA tab, the Preprocessing tab and the report all read from it:

```python
Finding = {
  "column": "Amount",
  "rule": "skewness",
  "stats": {"skewness": 16.98, "min": 0.0},          # the numbers quoted in the reason
  "recommendation": "log1p",
  "reason": "Skewness 16.98 > 1 and min >= 0, so log1p reduces the right tail.",
  "alternatives": [{"option": "yeo_johnson", "tradeoff": "..."}, {"option": "none", "tradeoff": "..."}]
}
```

A column can have several findings, for example one for missing values, one for outliers, one for skewness and one for scaling. The user picks one option per finding.

**Profiling scope.** Findings that affect fitted transformations, such as imputation values, outlier fences, skewness and scaling, use statistics computed on the **train split**. That is why the split happens right after configuration and before profiling. Purely descriptive EDA (distributions and correlations) is also shown on train, so all the numbers stay consistent. Duplicates and the class ratio are reported on the full dataset, because those checks happen before the split.

**API** (JSON; the session ID is returned when the file is uploaded):

| Endpoint | Purpose |
|---|---|
| `POST /upload` | Accept CSV/XLSX (with an optional `sheet`). Return the session ID, sheet names, columns, inferred types and row count. |
| `POST /configure` | Set the mode (supervised/unsupervised) and the target. Remove duplicate rows and rows with a missing target, split the data, then profile it and generate findings. |
| `GET /eda` | Per-column stats and chart data, plus missing values, duplicates, outliers and the correlation matrix. |
| `GET /findings` | All findings, grouped by column. |
| `POST /preview` | Take a column and the chosen options. Fit on train and return before/after stats and histograms for that column. |
| `POST /apply` | Take all choices. Fit the pipeline on train and transform train and test. |
| `GET /export` | Zip containing `train.csv`, `test.csv` and `report.xlsx`. |

**Order of operations in `/apply`.** Each fitted step is fitted on train, then applied to train and test:

1. Drop the columns the user chose to drop: constant, ID-like, too-many-missing, highly correlated.
2. Datetime feature extraction.
3. Imputation.
4. Outlier capping.
5. Skewness transform.
6. Categorical encoding.
7. Scaling.

The target column is never transformed. If the user chooses "drop rows" for missing values or outliers, the rows are dropped from **train only**. Test rows are imputed or capped with the train statistics instead, so test still reflects reality.

**Findings are computed once, except scaling (my call).** All findings are computed in `/configure` on the raw train data, so the screen, preview and report quote the same numbers. The exception is rule 9 (scaling). It runs last, after any capping or log transform, so it is evaluated on that column's train data *after* the user's chosen earlier steps. Whenever the user changes an earlier choice, `/preview` recomputes it and returns it, and the card updates. The report stores the version that was actually applied. "Preview" runs every chosen step for that column, in pipeline order, and shows raw train next to the result.

**Column types (my call).** Types are inferred automatically:
- **numeric:** numeric dtype with more than 10 unique values
- **categorical:** text, bool, or an integer with 10 or fewer unique values (e.g. Pclass, SibSp)
- **datetime:** text where at least 90% of non-null values parse with `pd.to_datetime`

On the configure step, the user gets a type dropdown for each column to override the inferred type. It costs one field in `/configure` and avoids silly findings on a second dataset.

**Live demo** runs locally (two dev servers on the laptop). No hosting.

**Supervised target type.** If the target is non-numeric, or numeric with 20 or fewer unique values, it is treated as **classification**: stratified split plus an imbalance report. Binary and multiclass targets go through the same code. Otherwise the target is treated as **regression**: plain random split, no imbalance check and no outlier signal check. If any class has fewer than 2 rows, stratifying is impossible. In that case the app falls back to a random split and shows a warning in the UI and the report (my call).

**Translations.** All user-facing text lives in `backend/app/i18n.py`, a single dictionary keyed by message ID with `{placeholders}` for numbers. The backend sends finished strings, and the frontend's fixed labels come from the same file, served through `GET /labels`. Changing the language means editing one file.

## 7. UI

```
[ Import ] [ EDA ] [ Preprocessing ] [ Export ]

Preprocessing tab — one card per column:
┌ Amount (numeric) ─────────────────────────────────────────────┐
│ missing 0.0% · skew 16.98 · IQR outliers 11.2% · min 0 · max …│
│ Skewness   ► Recommended: log1p — "skew 16.98 > 1, min ≥ 0"   │
│              ( ) log1p  ( ) Yeo-Johnson  ( ) none             │
│ Outliers   ► Recommended: none — "fraud rate in outliers …"   │
│              ( ) cap at IQR fences  ( ) drop rows  ( ) none   │
│ Scaling    ► Recommended: RobustScaler — "outliers 11.2% > 5%"│
│ [Preview before/after]  → two histograms + stats side by side │
└───────────────────────────────────────────────────────────────┘
```

The EDA tab has a column table (type, missing %, unique count, mean, std, min, max, skewness, outlier %), a chart for each column (a histogram, or a bar chart for categorical columns), a correlation heatmap, and a dataset banner showing rows, duplicates, split sizes and the class ratio.

## 8. Rules and thresholds (one-sentence defence each)

Rules run in the order below. A column that gets a drop recommendation still lists its other findings, so the user can override.

| # | Rule | Applies to | Trigger → recommendation | Alternatives | Why this threshold (say it out loud) |
|---|---|---|---|---|---|
| 1 | Duplicates | Dataset | Any exact duplicate rows → remove before splitting | keep | A duplicated row could land in both train and test, which leaks test answers into training. |
| 2 | Constant / near-constant | Column | 1 unique value, or the top value covers ≥ 99% of rows → drop | keep | A column that is the same for 99% of rows carries almost no information to learn from. |
| 3 | ID-like | Integer or text column | Unique ratio ≥ 95% → drop | keep | When nearly every value is unique, the column identifies rows rather than describing them, and a model would memorise it. |
| 4 | Missing (high) | Column | Missing > 50% → drop column | impute (mean, median, mode, constant), none | With more than half the values missing, any imputed value would be mostly invented. |
| 5 | Missing (impute) | Numeric | 0 < missing ≤ 50%: median if \|skew\| > 1, otherwise mean | mean, median, constant, drop rows (train only), drop column, none | The mean is pulled by a long tail when \|skew\| > 1, so the median is the more typical value. |
| 5b | Missing (impute) | Categorical | 0 < missing ≤ 50% → mode | constant "Missing", drop rows (train only), drop column, none | The most frequent category is the least surprising fill-in; "Missing" is the alternative when missingness itself may carry meaning. |
| 6 | Outliers | Numeric | IQR rule (outside Q1 − 1.5·IQR, Q3 + 1.5·IQR). If > 0%: cap at the fences when outlier share ≤ 5%; none when > 5% (heavy tail, handled by robust scaling); none when the outliers' target rate ≥ 2× the overall rate (supervised classification) | cap, drop rows (train only), none | 1.5·IQR is the standard Tukey fence; above 5% the "outliers" are part of the real distribution, and if fraud is twice as common among outliers they are signal, not noise. |
| 7 | Skewness | Numeric | \|skew\| > 1 → log1p if min ≥ 0, otherwise Yeo-Johnson | log1p, Yeo-Johnson, sqrt (if min ≥ 0), none | \|skew\| > 1 is the conventional "highly skewed" cut-off, and log1p only works on non-negative values, hence Yeo-Johnson otherwise. |
| 8 | Encoding | Categorical | ≤ 10 categories → one-hot; > 10 → frequency encoding | one-hot, ordinal, frequency, drop | Beyond 10 categories one-hot adds too many sparse columns; frequency encoding keeps a single column and is fitted on train counts. |
| 9 | Scaling | Numeric, after the steps above | Outlier share > 5% → RobustScaler; otherwise StandardScaler | Standard, MinMax, Robust, none | Robust scaling uses median and IQR, which stay stable when more than 5% of values are extreme; otherwise standardising to mean 0, std 1 is the default. |
| 10 | High correlation | Pair of numeric columns | \|Pearson r\| > 0.95 → drop the one with more missing values (tie: the later column) | keep both | Two features correlated above 0.95 carry almost the same information, and keeping both just duplicates it. |
| 11 | Datetime | Column parsed as dates | → extract year, month, day, day-of-week, then drop the original | drop, keep as-is | A raw timestamp isn't usable by most models, but its calendar parts are. |
| 12 | Imbalance | Target (binary or multiclass) | Smallest class ÷ largest class < 0.2 → recommend `class_weight="balanced"` (recorded only, no resampling) | none | When the rarest class is under a fifth the size of the largest, a model can score well by ignoring it, and class weights correct this without inventing rows; a ratio, unlike a share, works for any number of classes. |
| 13 | Free text | Text column not categorical, ID-like or datetime: > 50 unique values and mean length > 30 characters | → flag "free text, not processed", recommend drop | keep as-is (excluded from transforms) | Long, mostly unique strings are prose, which needs NLP rather than cleaning, so flagging it is more honest than encoding it. |

Rule 11 extension: a text column where 50–90% of values parse as dates is **flagged as "possible date, inconsistent format"**. The recommendation is to drop it, with "keep as-is" as the alternative, and no extraction is attempted.

**Never crash (my call):** each rule runs inside a guard. If a rule raises an error on some column, that column gets an "analysis failed" finding with the error message, and the default option is "none". The rest of the dataset still processes normally.

**Rule 6, order of checks (my call):** the signal check is evaluated first, so if the outliers' target rate is at least 2× the overall rate, the recommendation is "none" whatever the outlier share. For multiclass targets, "target rate" means the rate of the minority class. For regression, the signal check is skipped.

Target encoding is deliberately not offered. Done naively it leaks the target, and doing it safely isn't worth the time.

## 9. Excel report (`report.xlsx`)

- **Dataset** sheet:
  - file name, mode, target, task (classification/regression)
  - rows before and after deduplication, duplicates removed
  - split method (stratified or random), train and test sizes
  - class ratio, plus the imbalance recommendation where relevant
- **Features** sheet, one row per column:
  - type
  - stats: missing %, unique count, mean, std, min, max, skewness, outlier %
  - anomalies detected
  - recommendation and reason (with numbers)
  - alternatives
  - **option actually applied**
  - whether it matched the recommendation
- **Correlations** sheet: the pairs above the threshold.

The report is generated from the same `Finding` objects and stored choices as the UI, so the numbers always match.

## 10. Demo and validation datasets

- **Fraud demo:** Kaggle "Credit Card Fraud Detection" (`creditcard.csv`). It has no missing values and no categorical columns, so it shows off skewness, outliers, scaling, the outlier-signal rule and imbalance. It will **not** demonstrate imputation or encoding.
- **The instructor may bring an unseen dataset**, so the hardening above applies. For testing, use these:
  - a regression dataset, e.g. California housing from scikit-learn
  - a multiclass dataset, e.g. Iris or wine
  - a multi-sheet `.xlsx` with a free-text and a messy-date column, built by hand
- **Our own second dataset (proposal):** Titanic. It has missing values (Age, Cabin, Embarked), categorical columns, an ID column (PassengerId) and a binary target, so it covers the rules the fraud data doesn't.

## 11. Left to the builder

- Exact component structure and styling in React.
- How to bin histograms and how many rows to sample for scatter plots (keep responses fast on 285k rows).
- Error handling for unreadable files and the wording of messages.
- How tests are organised. At minimum, each rule gets a test with a hand-built DataFrame that triggers it and one that doesn't, plus a leakage test proving the fitted statistics come from train only.
- README with setup and run commands for both apps.
