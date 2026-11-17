# Smart Cleaner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React + FastAPI web app that profiles any CSV/Excel dataset, recommends a cleaning step per column with numeric justification and all alternatives, applies the user's choices fitted on train only, and exports `train.csv`, `test.csv` and `report.xlsx` in a zip.

**Architecture:** The FastAPI backend keeps each uploaded dataset in an in-memory session. It splits the data, profiles it, runs a rule engine that emits `Finding` objects, and fits per-column transforms on train. The React frontend only renders what the backend returns. Every user-facing string comes from one translations file.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pandas, numpy, scipy, scikit-learn, openpyxl, python-multipart, pytest, httpx. Node 24, Vite, React, react-plotly.js + plotly.js-dist-min, vitest.

**Spec:** [docs/superpowers/specs/2026-11-17-smart-cleaner-design.md](../specs/2026-11-17-smart-cleaner-design.md)

## Global Constraints

- All user-facing text (UI labels, reasons, trade-offs, report headers, warnings) comes from `backend/app/i18n.py`, in **English**. No user-facing literals anywhere else, frontend included (it gets labels from `GET /labels`).
- Split: 80/20, `random_state=42`. Classification targets are **stratified**. Regression and unsupervised use a **plain random split**. If any class has fewer than 2 rows, fall back to random and add a warning.
- Classification means the target is non-numeric, or numeric with ≤ 20 unique values. Otherwise the task is regression.
- Every fitted statistic (imputation value, IQR fences, encoder maps, scaler parameters, transform parameters) is computed on **train only**. Test is transformed, never fitted.
- Row drops ("drop rows") apply to **train only**. Test rows get imputed or capped with the train statistics.
- The target column is never transformed.
- **No SMOTE or resampling.** Imbalance means a recorded `class_weight="balanced"` recommendation and nothing more.
- No target encoding, no login, no database, no `.pkl` export.
- Thresholds (verbatim from spec §8):
  - near-constant: top value ≥ 99%
  - ID-like: unique ratio ≥ 95% (integer/text)
  - missing: > 50% → drop column; median if |skew| > 1, else mean
  - outliers: IQR 1.5; cap if share ≤ 5%; signal if outlier target rate ≥ 2× overall (checked first)
  - skewness: |skew| > 1 (log1p if min ≥ 0, else Yeo-Johnson)
  - one-hot: ≤ 10 categories, frequency above that
  - scaling: Robust if outlier share > 5%, else Standard
  - correlation: |r| > 0.95
  - imbalance: smallest/largest < 0.2
  - free text: > 50 unique and mean length > 30
  - datetime: ≥ 90% parse → datetime; 50–90% → flag
  - categorical: integer with ≤ 10 unique values
- Never crash on a column: any rule exception becomes an `analysis_failed` finding with default option `none`.

## Review Focus

1. **A French/European CSV** (`;` separator, `,` decimal) is read into proper numeric columns, not a single text column. Test in Task 2.
2. **Test-set categories unseen in train**, or NaN at encoding time, don't crash. One-hot gives all zeros, frequency gives 0, ordinal gives −1. Test in Task 12.
3. **A column that is entirely missing in train**, or has one non-null value, produces findings (`missing` → drop column) with no exception and no NaN in the JSON. Test in Task 10.
4. **log1p fitted on a train column with min ≥ 0, applied to a test column with negative values**, doesn't produce NaN or −inf. Test values are clipped to the train minimum first. Test in Task 11.
5. **A 300k-row dataset**: EDA chart data stays bounded (≤ 30 histogram bins, ≤ 20 bars per categorical column, a correlation matrix over numeric columns only), so the payload doesn't scale with the row count. Test in Task 3.

---

## File structure

```
backend/
  requirements.txt
  pytest.ini
  app/
    __init__.py
    i18n.py          # MESSAGES dict + t(key, **kw)
    io.py            # read_table: CSV (delimiter sniffing) / Excel (sheet choice)
    types.py         # infer_types
    findings.py      # Finding, Alternative dataclasses + option constants
    profiling.py     # column_stats, chart_data, correlation_matrix
    split.py         # prepare_and_split -> SplitResult
    rules/
      __init__.py
      context.py     # ColumnContext
      structural.py  # constant, id_like, free_text, datetime
      missing.py
      distribution.py# outliers, skewness
      encoding.py    # encoding, scaling
      dataset.py     # duplicates, correlation, imbalance
    engine.py        # run_rules (guarded)
    transforms.py    # ColumnPipeline, apply_all
    preview.py       # preview_column
    report.py        # build_report, build_zip
    session.py       # Session store
    main.py          # FastAPI routes
  tests/
    conftest.py      # shared small DataFrames
    test_*.py
frontend/
  (Vite React app)
  src/api.js, src/choices.js, src/App.jsx, src/tabs/*.jsx, src/components/*.jsx
README.md
```

Run all backend tests from `backend/`: `.venv/Scripts/python -m pytest -q`. On Windows Git Bash, use `.venv/Scripts/python`.

---

### Task 1: Backend scaffold and translations

**Files:**
- Create: `backend/requirements.txt`, `backend/pytest.ini`, `backend/app/__init__.py`, `backend/app/i18n.py`, `backend/tests/__init__.py`, `backend/tests/test_i18n.py`

**Interfaces:**
- Produces: `MESSAGES: dict[str, str]` and `t(key: str, **kw) -> str` in `app.i18n`. Keys are dotted, e.g. `"reason.skewness.log1p"`, `"tradeoff.median"`, `"ui.tab.eda"`. `t` formats `{placeholders}`; numbers are passed pre-rounded by callers. `ui_labels() -> dict[str, str]` returns every key starting with `ui.`.

- [ ] **Step 1: Create the venv and install dependencies**

`requirements.txt`: fastapi, uvicorn[standard], pandas, numpy, scipy, scikit-learn, openpyxl, python-multipart, pytest, httpx.
Run (from `backend/`): `py -3.12 -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`
Expected: install completes. Add `pythonpath = .` and `testpaths = tests` to `pytest.ini`.

- [ ] **Step 2: Write the failing test**

```python
from app.i18n import t, ui_labels, MESSAGES

def test_t_formats_placeholders():
    MESSAGES["test.key"] = "Skewness {skew} > 1"
    assert t("test.key", skew=2.5) == "Skewness 2.5 > 1"

def test_missing_key_raises():
    import pytest
    with pytest.raises(KeyError):
        t("does.not.exist")

def test_ui_labels_only_ui_keys():
    labels = ui_labels()
    assert labels and all(k.startswith("ui.") for k in labels)
```

- [ ] **Step 3: Run it to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_i18n.py -q`. Expected: FAIL with `ModuleNotFoundError: app.i18n`.

- [ ] **Step 4: Implement `t` and `ui_labels` in `app/i18n.py`**

Seed `MESSAGES` with the four tab names (`ui.tab.import`, `ui.tab.eda`, `ui.tab.preprocessing`, `ui.tab.export`). Later tasks add their own keys to this file.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_i18n.py -q`. Expected: 3 passed.

- [ ] **Step 6: Commit**

`git add backend && git commit -m "feat(backend): scaffold and i18n"`. The `.gitignore` already excludes `.venv/`.

---

### Task 2: File reading and type inference

**Files:**
- Create: `backend/app/io.py`, `backend/app/types.py`, `backend/tests/test_io.py`, `backend/tests/test_types.py`

**Interfaces:**
- Produces:
  - `read_table(content: bytes, filename: str, sheet: str | None = None) -> tuple[pd.DataFrame, list[str]]` returns the DataFrame and the sheet names (`[]` for CSV). Raises `ValueError(t("error.unreadable_file"))` on failure.
  - `infer_types(df: pd.DataFrame) -> dict[str, str]` with values in `{"numeric", "categorical", "datetime"}`.
  - `apply_type_overrides(types: dict[str, str], overrides: dict[str, str]) -> dict[str, str]`.

- [ ] **Step 1: Write the failing tests**

```python
# test_io.py
def test_reads_semicolon_csv_with_comma_decimal():
    df, sheets = read_table(b"a;b\n1,5;x\n2,5;y\n", "f.csv")
    assert list(df.columns) == ["a", "b"] and df["a"].tolist() == [1.5, 2.5] and sheets == []

def test_reads_comma_csv():
    df, _ = read_table(b"a,b\n1,x\n2,y\n", "f.csv")
    assert df.shape == (2, 2)

def test_excel_lists_sheets_and_reads_chosen_one(tmp_path):
    # write a 2-sheet xlsx with pandas.ExcelWriter, sheets "first" and "second"
    df, sheets = read_table(xlsx_bytes, "f.xlsx", sheet="second")
    assert sheets == ["first", "second"] and df.equals(second_df)

def test_excel_defaults_to_first_sheet(): ...  # sheet=None -> first sheet

def test_garbage_raises_value_error():
    with pytest.raises(ValueError):
        read_table(b"\x00\x01\x02", "f.xlsx")

# test_types.py
def test_infer_types():
    df = pd.DataFrame({
        "amount": np.arange(100) * 1.5,                     # numeric
        "pclass": [1, 2, 3, 1] * 25,                        # int <=10 unique -> categorical
        "city": ["a", "b"] * 50,                            # categorical
        "when": pd.date_range("2020-01-01", periods=100).astype(str),  # datetime
        "flag": [True, False] * 50,                         # categorical
    })
    assert infer_types(df) == {"amount": "numeric", "pclass": "categorical",
                               "city": "categorical", "when": "datetime", "flag": "categorical"}

def test_mostly_unparseable_dates_stay_categorical():
    s = ["2020-01-01"] * 6 + ["garbage"] * 4   # 60% parse -> not datetime (flagged later by rule 11)
    assert infer_types(pd.DataFrame({"d": s}))["d"] == "categorical"

def test_overrides_replace_types():
    assert apply_type_overrides({"a": "numeric"}, {"a": "categorical"}) == {"a": "categorical"}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_io.py tests/test_types.py -q`. Expected: FAIL (modules missing).

- [ ] **Step 3: Implement `read_table`**

CSV: run `csv.Sniffer().sniff` on the first 64 KB with delimiters `",;\t|"` (fall back to `,`). If the separator is `;`, pass `decimal=","`. Decode as `utf-8-sig`, falling back to `latin-1`. Excel: `pd.ExcelFile` gives `sheet_names`, and `parse(sheet or sheet_names[0])`. Use the extension to decide (`.xlsx`/`.xls` means Excel). Add the key `error.unreadable_file` to i18n.

- [ ] **Step 4: Implement `infer_types` and `apply_type_overrides`**

- **numeric:** numeric dtype (excluding bool) with more than 10 unique values.
- **datetime:** an object column where ≥ 90% of non-null values parse with `pd.to_datetime(errors="coerce", format="mixed")`. Check at most the first 1000 non-null values for speed.
- **categorical:** everything else.

- [ ] **Step 5: Run the tests to verify they pass**

Run the same command. Expected: all pass.

- [ ] **Step 6: Commit**

`git commit -am "feat(backend): table reading and type inference"` (add the new files first).

---

### Task 3: Finding model and profiling

**Files:**
- Create: `backend/app/findings.py`, `backend/app/profiling.py`, `backend/tests/conftest.py`, `backend/tests/test_profiling.py`

**Interfaces:**
- Produces:
  - `@dataclass Alternative(option: str, tradeoff: str)`.
  - `@dataclass Finding(column: str | None, rule: str, stats: dict[str, float | int | str], recommendation: str, reason: str, alternatives: list[Alternative], severity: str = "info")`, with `to_dict() -> dict`. Every `Alternative` list **includes the recommended option itself**, so the UI can render one radio group. `column` is `None` for dataset-level findings.
  - Rule names, as module constants in `findings.py`: `DUPLICATES, CONSTANT, ID_LIKE, FREE_TEXT, DATETIME, MISSING, OUTLIERS, SKEWNESS, ENCODING, SCALING, CORRELATION, IMBALANCE, ANALYSIS_FAILED`, with string values in lowercase snake case (`"id_like"`, etc.).
  - Option strings: `none, keep, drop_column, drop_rows, mean, median, mode, constant, constant_missing, cap, log1p, yeo_johnson, sqrt, onehot, ordinal, frequency, standard, minmax, robust, extract, remove, class_weight_balanced`.
  - `round_stat(x) -> float | None`: 4 significant figures, and NaN/inf become `None`, so the JSON is always valid.
  - `column_stats(s: pd.Series, col_type: str) -> dict`:
    - always: `missing_pct, n_unique, unique_ratio, top_freq_pct`
    - numeric adds: `mean, std, min, max, skewness, outlier_pct, q1, q3, lower_fence, upper_fence` (IQR 1.5, computed on non-null values)
    - categorical adds: `mean_length`
  - `chart_data(s: pd.Series, col_type: str) -> dict`:
    - numeric: `{"kind": "histogram", "edges": [...], "counts": [...]}` with ≤ 30 bins
    - categorical: `{"kind": "bar", "labels": [...], "counts": [...]}` with the top 19 plus "Other", so ≤ 20 bars
  - `correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> {"columns": [...], "matrix": [[...]]}`, Pearson, with NaN → `None`.
- conftest fixtures: `mixed_df` (numeric skewed column with missing values, categorical column, constant column, id column, binary target) and `numeric_series_with_outliers`.

- [ ] **Step 1: Write the failing tests**

```python
def test_numeric_stats(numeric_series_with_outliers):
    st = column_stats(numeric_series_with_outliers, "numeric")
    assert st["missing_pct"] == 0 and st["outlier_pct"] > 0 and "skewness" in st

def test_stats_on_all_missing_column_are_json_safe():
    st = column_stats(pd.Series([np.nan] * 10), "numeric")
    assert st["missing_pct"] == 100 and st["mean"] is None and st["skewness"] is None

def test_histogram_bounded_on_large_column():
    cd = chart_data(pd.Series(np.random.default_rng(0).normal(size=300_000)), "numeric")
    assert cd["kind"] == "histogram" and len(cd["counts"]) <= 30

def test_bar_chart_bounded():
    cd = chart_data(pd.Series([f"c{i}" for i in range(500)]), "categorical")
    assert len(cd["labels"]) <= 20 and cd["labels"][-1] == "Other"

def test_correlation_numeric_only(mixed_df): ...  # columns == numeric_cols passed in

def test_finding_to_dict_roundtrip():
    f = Finding("a", "skewness", {"skewness": 2.0}, "log1p", "r", [Alternative("log1p", "x")])
    assert f.to_dict()["alternatives"][0] == {"option": "log1p", "tradeoff": "x"}
```

- [ ] **Step 2: Run them to verify they fail.** Run `.venv/Scripts/python -m pytest tests/test_profiling.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement `findings.py` and `profiling.py`** to the signatures above. Skewness is `scipy.stats.skew(bias=False)` on non-null values, or `None` if there are fewer than 3. Add the label `"Other"` as an i18n key (`ui.other`).

- [ ] **Step 4: Run the tests to verify they pass.** Expected: all pass.

- [ ] **Step 5: Commit.** `git add backend && git commit -m "feat(backend): finding model and profiling"`

---

### Task 4: Preparation and split

**Files:**
- Create: `backend/app/split.py`, `backend/tests/test_split.py`

**Interfaces:**
- Produces:
  - `detect_task(y: pd.Series) -> str` returns `"classification"` or `"regression"`.
  - `@dataclass SplitResult(train: pd.DataFrame, test: pd.DataFrame, task: str | None, stratified: bool, n_rows_raw: int, n_duplicates: int, n_target_missing: int, warnings: list[str])`.
  - `prepare_and_split(df: pd.DataFrame, mode: str, target: str | None, seed: int = 42) -> SplitResult`. `mode` is `"supervised"` or `"unsupervised"`. This function removes exact duplicate rows and, when supervised, rows with a missing target. It then splits 80/20.

- [ ] **Step 1: Write the failing tests**

```python
def test_detect_task():
    assert detect_task(pd.Series([0, 1] * 50)) == "classification"
    assert detect_task(pd.Series(["a", "b", "c"] * 10)) == "classification"
    assert detect_task(pd.Series(np.linspace(0, 1, 100))) == "regression"

def test_duplicates_removed_before_split():
    df = pd.DataFrame({"x": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "y": [0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]})
    r = prepare_and_split(df, "supervised", "y")
    assert r.n_duplicates == 1 and len(r.train) + len(r.test) == 10

def test_stratified_keeps_class_ratio():
    df = pd.DataFrame({"x": range(1000), "y": [1] * 50 + [0] * 950})
    r = prepare_and_split(df, "supervised", "y")
    assert r.stratified and r.task == "classification"
    assert abs(r.test["y"].mean() - 0.05) < 0.01 and len(r.test) == 200

def test_missing_target_rows_dropped(): ...  # n_target_missing == count; no NaN in train/test target

def test_unsupervised_random_split():
    r = prepare_and_split(pd.DataFrame({"x": range(100)}), "unsupervised", None)
    assert r.task is None and not r.stratified and len(r.test) == 20

def test_regression_not_stratified(): ...  # task == "regression", stratified False

def test_singleton_class_falls_back_with_warning():
    df = pd.DataFrame({"x": range(100), "y": [0] * 60 + [1] * 39 + [2]})
    r = prepare_and_split(df, "supervised", "y")
    assert not r.stratified and r.warnings
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.

- [ ] **Step 3: Implement** using `sklearn.model_selection.train_test_split(test_size=0.2, random_state=seed, stratify=...)`. Add the i18n key `warning.stratify_fallback` (it mentions the class and its count).

- [ ] **Step 4: Run the tests to verify they pass.** Expected: all pass.

- [ ] **Step 5: Commit.** `git commit -m "feat(backend): dedupe and leakage-safe split"`

---

### Task 5: Structural rules (constant, ID-like, free text, datetime)

**Files:**
- Create: `backend/app/rules/__init__.py`, `backend/app/rules/context.py`, `backend/app/rules/structural.py`, `backend/tests/test_rules_structural.py`
- Modify: `backend/tests/conftest.py` (add `ctx_for(s, col_type, target=None, task=None) -> ColumnContext`)

**Interfaces:**
- Consumes: `Finding`, `Alternative`, the rule and option constants, `column_stats` output, `t`.
- Produces:
  - `@dataclass ColumnContext(col_type: str, stats: dict, target: pd.Series | None, task: str | None)`. `target` is the train target aligned to the series.
  - Each rule is `check_<rule>(s: pd.Series, ctx: ColumnContext) -> Finding | None` in `structural.py`: `check_constant`, `check_id_like`, `check_free_text`, `check_datetime`.
  - Reasons use `t("reason.<rule>.<recommendation>", ...)` and quote the stats. Trade-offs use `t("tradeoff.<option>")`.

Rules and options (spec §8):

| Function | Fires when | Recommendation | Alternatives (all listed, recommendation included) |
|---|---|---|---|
| `check_constant` | `n_unique <= 1` or `top_freq_pct >= 99` | `drop_column` | `drop_column, keep` |
| `check_id_like` | type numeric with an integer dtype, or categorical; and `unique_ratio >= 0.95` | `drop_column` | `drop_column, keep` |
| `check_free_text` | categorical, not ID-like by the rule above, `n_unique > 50` and `mean_length > 30` | `drop_column`, severity `"warning"` | `drop_column, keep` |
| `check_datetime` | type datetime → `extract`. Categorical with 50% ≤ parse rate < 90% → `drop_column`, severity `"warning"` ("possible date, inconsistent format") | as stated | datetime: `extract, drop_column, keep`. Flag: `drop_column, keep` |

- [ ] **Step 1: Write the failing tests**, one firing case and one non-firing case per rule:

```python
def test_constant_fires_at_99_pct():
    s = pd.Series([1] * 99 + [2]); f = check_constant(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column" and f.stats["top_freq_pct"] == 99.0
    assert "99" in f.reason and {a.option for a in f.alternatives} == {"drop_column", "keep"}

def test_constant_not_fired_at_98_pct(): ...          # returns None
def test_id_like_fires_on_unique_ints(): ...          # range(100) as int -> drop_column
def test_id_like_ignores_continuous_floats(): ...     # normal floats -> None
def test_free_text_fires_on_long_unique_strings(): ...# 60 distinct 40-char strings, but ratio < 0.95 by repeating
def test_free_text_ignores_short_categories(): ...
def test_datetime_extract(): ...                      # col_type "datetime" -> "extract"
def test_inconsistent_dates_flagged():
    s = pd.Series(["2020-01-01"] * 6 + ["junk"] * 4)
    f = check_datetime(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column" and f.severity == "warning"
```

`ctx_for(s, type)` is a conftest helper that builds a `ColumnContext` from `column_stats`.

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.

- [ ] **Step 3: Implement the four checks and their i18n keys** (`reason.constant.drop_column`, `tradeoff.keep`, …). Every reason sentence includes the threshold and the measured value.

- [ ] **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(rules): constant, id-like, free text, datetime"`

---

### Task 6: Missing-values rule

**Files:**
- Create: `backend/app/rules/missing.py`, `backend/tests/test_rules_missing.py`

**Interfaces:**
- Produces: `check_missing(s: pd.Series, ctx: ColumnContext) -> Finding | None`. Returns nothing when `missing_pct == 0`.

| Condition | Recommendation | Alternatives |
|---|---|---|
| `missing_pct > 50` | `drop_column` | numeric: `drop_column, mean, median, constant, drop_rows, none`. Categorical: `drop_column, mode, constant_missing, drop_rows, none` |
| numeric, 0 < pct ≤ 50, `skewness is not None and abs(skewness) > 1` | `median` | `median, mean, constant, drop_rows, drop_column, none` |
| numeric, otherwise | `mean` | same set |
| categorical/datetime | `mode` | `mode, constant_missing, drop_rows, drop_column, none` |

- [ ] **Step 1: Write the failing tests**

```python
def test_no_missing_no_finding(): ...
def test_over_50_pct_drops_column(): ...                 # 60% NaN -> drop_column, reason quotes 60
def test_skewed_numeric_gets_median():
    s = pd.Series(list(np.random.default_rng(0).exponential(size=90)) + [np.nan] * 10)
    f = check_missing(s, ctx_for(s, "numeric"))
    assert f.recommendation == "median" and abs(f.stats["skewness"]) > 1
def test_symmetric_numeric_gets_mean(): ...
def test_categorical_gets_mode_with_missing_alternative(): ...  # "constant_missing" in alternatives
def test_drop_rows_tradeoff_says_train_only():
    assert "train" in t("tradeoff.drop_rows").lower()
```

- [ ] **Step 2: Run them to verify they fail.**

- [ ] **Step 3: Implement it, adding the i18n keys.**

- [ ] **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(rules): missing values"`

---

### Task 7: Outliers and skewness rules

**Files:**
- Create: `backend/app/rules/distribution.py`, `backend/tests/test_rules_distribution.py`

**Interfaces:**
- Produces: `check_outliers(s, ctx) -> Finding | None` and `check_skewness(s, ctx) -> Finding | None`, for numeric columns only. Also `outlier_target_rates(s, ctx) -> tuple[float, float] | None`, which returns the rate in the outlier rows and the overall rate, or `None` when the task isn't classification.

**Outliers** (fires only when `outlier_pct > 0`), evaluated in this order:
1. **Classification task:** the rate of the **smallest class** among outlier rows is ≥ 2× its overall rate → `none`. The reason quotes both rates. For binary targets the smallest class is the fraud class.
2. `outlier_pct <= 5` → `cap`.
3. Otherwise → `none`. The reason says the tail is heavy and points to robust scaling.

Alternatives are always `cap, drop_rows, none`.

**Skewness** fires when `abs(skewness) > 1`. If `min >= 0` it recommends `log1p`, with alternatives `log1p, yeo_johnson, sqrt, none`. Otherwise it recommends `yeo_johnson`, with alternatives `yeo_johnson, none`.

- [ ] **Step 1: Write the failing tests**

```python
def test_few_outliers_capped(): ...            # 2% outliers, no target -> "cap"
def test_many_outliers_none(): ...             # 10% outliers -> "none"
def test_signal_overrides_low_share():
    # 1000 rows, 2% outliers, fraud rate 50% among outliers vs 2% overall
    f = check_outliers(s, ctx_with_target)
    assert f.recommendation == "none" and f.stats["outlier_target_rate"] >= 2 * f.stats["overall_target_rate"]
def test_signal_skipped_for_regression(): ...  # task "regression" -> share rule applies
def test_no_outliers_no_finding(): ...
def test_positive_skew_log1p(): ...            # exponential -> log1p; sqrt in alternatives
def test_negative_values_yeo_johnson(): ...    # skewed with min < 0 -> yeo_johnson, no log1p/sqrt offered
def test_symmetric_no_skew_finding(): ...
```

- [ ] **Step 2: Run them to verify they fail.**

- [ ] **Step 3: Implement it.** The outlier mask uses the train fences from `ctx.stats` (`lower_fence`, `upper_fence`).

- [ ] **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(rules): outliers and skewness"`

---

### Task 8: Encoding and scaling rules

**Files:**
- Create: `backend/app/rules/encoding.py`, `backend/tests/test_rules_encoding.py`

**Interfaces:**
- Produces:
  - `check_encoding(s, ctx) -> Finding | None` for categorical columns. If `n_unique <= 10` it recommends `onehot`, otherwise `frequency`. Alternatives are always `onehot, ordinal, frequency, drop_column`.
  - `check_scaling(s, ctx) -> Finding` for numeric columns, and it always fires. If `outlier_pct > 5` it recommends `robust`, otherwise `standard`. Alternatives are `standard, minmax, robust, none`.
  - **Recomputation:** `check_scaling` is called again by `preview_column` (Task 13) and `apply_all` (Task 12) on the column *after* its earlier steps, passing a fresh `ColumnContext` built from `column_stats` of the transformed series.

- [ ] **Step 1: Write the failing tests**

```python
def test_low_cardinality_onehot(): ...
def test_high_cardinality_frequency(): ...     # 11 categories -> frequency
def test_numeric_not_encoded(): ...            # returns None for numeric
def test_scaling_robust_when_many_outliers(): ...
def test_scaling_standard_otherwise(): ...
def test_scaling_recomputed_after_capping_changes_recommendation():
    s = heavy_tail_series            # outlier_pct > 5 -> robust
    capped = s.clip(stats["lower_fence"], stats["upper_fence"])
    assert check_scaling(capped, ctx_for(capped, "numeric")).recommendation == "standard"
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it.**  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(rules): encoding and scaling"`

---

### Task 9: Dataset-level rules (duplicates, correlation, imbalance)

**Files:**
- Create: `backend/app/rules/dataset.py`, `backend/tests/test_rules_dataset.py`

**Interfaces:**
- Produces:
  - `check_duplicates(n_duplicates: int, n_rows_raw: int) -> Finding | None`. Column `None`, recommendation `remove`, alternatives `remove` only, with a trade-off explaining that removal already happened before the split. Returns `None` when the count is 0.
  - `check_correlation(train: pd.DataFrame, numeric_cols: list[str], missing_pct: dict[str, float]) -> list[Finding]`. One finding per pair with `|r| > 0.95`. The finding's `column` is the column to drop: the one with more missing values, or the later one in `numeric_cols` on a tie. Its stats are `{"other": name, "r": value}`. Alternatives are `drop_column, keep`.
  - `check_imbalance(y_train: pd.Series) -> Finding | None`. Only for classification. Column = the target name. Stats are `class_counts` (as a string), `ratio` and `smallest_class`. If `ratio < 0.2` it recommends `class_weight_balanced`, with alternatives `class_weight_balanced, none`. It always returns a finding for classification, so the class ratio is always reported. When the ratio is ≥ 0.2 the recommendation is `none`.

- [ ] **Step 1: Write the failing tests**

```python
def test_duplicates_finding(): ...                 # n=3 -> stats n_duplicates 3, rec "remove"
def test_correlated_pair_drops_later_column():
    df = pd.DataFrame({"a": x, "b": x * 2 + 0.001 * noise, "c": other})
    fs = check_correlation(df, ["a", "b", "c"], {"a": 0, "b": 0, "c": 0})
    assert len(fs) == 1 and fs[0].column == "b" and fs[0].stats["other"] == "a"
def test_correlated_pair_drops_more_missing(): ...
def test_imbalance_binary(): ...                   # 5% vs 95% -> ratio ~0.0526, class_weight_balanced
def test_imbalance_multiclass_ratio(): ...         # counts 100/100/15 -> ratio 0.15 -> recommended
def test_balanced_multiclass_reports_none(): ...   # 5 equal classes -> rec "none"
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it.**  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(rules): duplicates, correlation, imbalance"`

---

### Task 10: Rule engine

**Files:**
- Create: `backend/app/engine.py`, `backend/tests/test_engine.py`

**Interfaces:**
- Consumes: every `check_*` function, `column_stats`, `SplitResult`.
- Produces: `run_rules(split: SplitResult, types: dict[str, str], target: str | None) -> tuple[list[Finding], dict[str, dict]]`, which returns the findings and the per-column stats on train. It runs over every column except the target, in this order: constant, id_like, free_text, datetime, missing, outliers, skewness, encoding, scaling. Then it runs the dataset rules: duplicates, correlation, and imbalance when the task is classification. Each column-rule call sits inside its own `try/except Exception`. On failure the engine appends `Finding(column, "analysis_failed", {"error": str(e)}, "none", t("reason.analysis_failed", error=...), [Alternative("none", ...)], severity="error")` and carries on.

- [ ] **Step 1: Write the failing tests**

```python
def test_mixed_df_findings(mixed_df):       # from conftest
    split = prepare_and_split(mixed_df, "supervised", "target")
    findings, stats = run_rules(split, infer_types(mixed_df), "target")
    rules_by_col = {(f.column, f.rule) for f in findings}
    assert ("const_col", "constant") in rules_by_col and ("id_col", "id_like") in rules_by_col
    assert all(f.column != "target" or f.rule == "imbalance" for f in findings)

def test_all_missing_column_does_not_crash():
    df = mixed_df.assign(empty=np.nan)
    findings, _ = run_rules(prepare_and_split(df, "supervised", "target"), infer_types(df), "target")
    f = next(f for f in findings if f.column == "empty" and f.rule == "missing")
    assert f.recommendation == "drop_column"
    json.dumps([f.to_dict() for f in findings])      # no NaN/inf -> serialisable with allow_nan=False
    json.dumps([f.to_dict() for f in findings], allow_nan=False)

def test_rule_exception_becomes_analysis_failed(monkeypatch):
    monkeypatch.setattr(engine, "check_skewness", lambda s, c: 1 / 0)
    findings, _ = run_rules(...)
    assert any(f.rule == "analysis_failed" and f.severity == "error" for f in findings)
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it** (call the checks through module-level names so `monkeypatch` works).  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(backend): guarded rule engine"`

---

### Task 11: Column pipeline: drop, datetime, imputation, outliers, skewness

**Files:**
- Create: `backend/app/transforms.py`, `backend/tests/test_transforms.py`

**Interfaces:**
- Consumes: option constants, `column_stats`.
- Produces: `class ColumnPipeline(column: str, col_type: str, choices: dict[str, str])`. `choices` maps a rule name to an option. A rule missing from `choices` means `none`.
  - `fit(train: pd.DataFrame) -> "ColumnPipeline"` fits steps in order on the train column only, and stores the fitted parameters in `self.params: dict`.
  - `transform(df: pd.DataFrame, is_train: bool) -> pd.DataFrame` returns a DataFrame with the output column(s) for this column, with the same index as the input. Rows are never removed here.
  - `train_rows_to_drop(train: pd.DataFrame) -> pd.Index` returns the train index labels removed by `drop_rows` choices (`missing` or `outliers`).
  - `dropped: bool` is True when any choice is `drop_column` (constant, id_like, free_text, datetime, missing, correlation, encoding).
  - `applied() -> dict[str, str]`, the options actually applied, for the report.

Steps and fitted parameters (this task covers steps 1–5; Task 12 covers 6–7):
1. **drop:** any `drop_column` → the output is empty and the other steps are skipped.
2. **datetime** `extract` → `<col>_year, _month, _day, _dayofweek`. NaT parts are filled with the train median of that part, then the original column is dropped.
3. **missing:**
   - `mean`, `median`, `mode`: computed on train.
   - `constant`: 0 for numeric, `"Missing"` for categorical.
   - `constant_missing`: `"Missing"`.
   - `drop_rows`: on train, rows are dropped via `train_rows_to_drop`. On test, NaN is filled with the train median (numeric) or mode (categorical).
4. **outliers:**
   - `cap`: clip to the train `lower_fence` and `upper_fence`.
   - `drop_rows`: on train, drop the rows outside the fences. On test, cap.
5. **skewness:**
   - `log1p`: clip to the train min first, then `np.log1p`.
   - `sqrt`: clip to the train min (≥ 0) first.
   - `yeo_johnson`: `sklearn.preprocessing.PowerTransformer(method="yeo-johnson", standardize=False)` fitted on train non-null values. NaN passes through.

- [ ] **Step 1: Write the failing tests**

```python
def test_median_from_train_only():
    train = pd.DataFrame({"x": [1, 2, 3, np.nan]}); test = pd.DataFrame({"x": [100, 200, np.nan]})
    p = ColumnPipeline("x", "numeric", {"missing": "median"}).fit(train)
    assert p.transform(test, is_train=False)["x"].iloc[2] == 2.0

def test_drop_rows_train_only():
    p = ColumnPipeline("x", "numeric", {"missing": "drop_rows"}).fit(train)
    assert list(p.train_rows_to_drop(train)) == [3]
    assert p.transform(test, is_train=False)["x"].isna().sum() == 0   # test imputed with train median

def test_cap_uses_train_fences(): ...      # test value 1e6 clipped to train upper_fence
def test_log1p_on_test_negative_is_finite():
    train = pd.DataFrame({"x": [0, 1, 2, 3, 100.0]}); test = pd.DataFrame({"x": [-5.0, 1.0]})
    out = ColumnPipeline("x", "numeric", {"skewness": "log1p"}).fit(train).transform(test, False)
    assert np.isfinite(out["x"]).all()

def test_yeo_johnson_fitted_on_train(): ... # params["skewness"] lambda equals PowerTransformer fit on train only
def test_drop_column_returns_empty(): ...   # dropped True, transform returns 0 columns
def test_datetime_extract(): ...           # 4 new int columns, original gone
def test_applied_reports_choices(): ...    # applied() == the non-"none" choices actually used
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement steps 1–5.**  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(transforms): drop, datetime, impute, outliers, skew"`

---

### Task 12: Encoding, scaling, and applying everything

**Files:**
- Modify: `backend/app/transforms.py`
- Test: `backend/tests/test_transforms.py`, `backend/tests/test_apply_all.py`

**Interfaces:**
- Produces:
  - Steps 6 and 7 inside `ColumnPipeline`:
    - **encoding:** `onehot` → `<col>_<category>` 0/1 columns for the train categories; NaN and unseen categories are all zeros. `ordinal` → train categories sorted, mapped to 0..k−1, unseen or NaN → −1. `frequency` → train relative frequency, unseen or NaN → 0.
    - **scaling:** `standard`, `minmax`, `robust`, fitted on the train values *after* steps 1–5, using pandas arithmetic so NaN passes through. A zero std, range or IQR → divide by 1.
  - `@dataclass ApplyResult(train: pd.DataFrame, test: pd.DataFrame, applied: dict[str, dict[str, str]], scaling_findings: dict[str, Finding], rows_dropped_train: int)`.
  - `apply_all(split: SplitResult, types: dict[str, str], choices: dict[str, dict[str, str]], target: str | None) -> ApplyResult`:
    1. Build a pipeline per non-target column and fit it on `split.train`.
    2. Collect the `train_rows_to_drop` from all pipelines.
    3. Transform train (without the dropped rows) and test.
    4. Concatenate the outputs, then append the target column unchanged.
    5. For every numeric non-dropped column, record `check_scaling` recomputed on the train column after steps 1–5, stored in `scaling_findings`.

- [ ] **Step 1: Write the failing tests**

```python
def test_onehot_unseen_category_all_zero():
    p = ColumnPipeline("c", "categorical", {"encoding": "onehot"}).fit(pd.DataFrame({"c": ["a", "b"]}))
    out = p.transform(pd.DataFrame({"c": ["z", np.nan]}), False)
    assert (out.to_numpy() == 0).all() and list(out.columns) == ["c_a", "c_b"]

def test_frequency_and_ordinal_unseen(): ...           # 0 and -1
def test_standard_scaler_uses_train_mean_std(): ...    # test value equals (v - train_mean)/train_std
def test_robust_scaler_zero_iqr_safe(): ...            # constant train -> no inf

def test_apply_all_no_leakage(mixed_df):
    split = prepare_and_split(mixed_df, "supervised", "target")
    choices = {"num": {"missing": "median", "scaling": "standard"}}
    r = apply_all(split, infer_types(mixed_df), choices, "target")
    num_train_after_impute = split.train["num"].fillna(split.train["num"].median())
    assert abs(r.train["num"].mean()) < 1e-9                       # standardised on train
    expected = (split.test["num"].fillna(split.train["num"].median()) - num_train_after_impute.mean()) / num_train_after_impute.std(ddof=0)
    pd.testing.assert_series_equal(r.test["num"], expected, check_names=False)

def test_apply_all_target_untouched_and_rows_dropped_train_only(): ...
def test_apply_all_records_scaling_finding_after_cap(): ...
```

Use `ddof=0` for StandardScaler parity, and keep it the same in the implementation.

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it.**  **Step 4: Run the full suite:** `.venv/Scripts/python -m pytest -q`. Expected: all pass.

- [ ] **Step 5: Commit.** `git commit -m "feat(transforms): encoding, scaling, apply_all"`

---

### Task 13: Before/after preview

**Files:**
- Create: `backend/app/preview.py`, `backend/tests/test_preview.py`

**Interfaces:**
- Consumes: `ColumnPipeline`, `column_stats`, `chart_data`, `check_scaling`, `ColumnContext`.
- Produces: `preview_column(train: pd.DataFrame, column: str, col_type: str, column_choices: dict[str, str]) -> dict` with:
  - `before`: `{"stats", "chart"}` for the raw train column
  - `after`: a list of `{"name", "stats", "chart"}`, one per output column, at most 20 (one-hot can be wide)
  - `scaling`: the recomputed scaling `Finding.to_dict()` or `None`
  - `rows_dropped`: an int

  It fits on train and transforms train with all chosen steps, in pipeline order.

- [ ] **Step 1: Write the failing tests**

```python
def test_preview_log_reduces_skew():
    r = preview_column(train, "amount", "numeric", {"skewness": "log1p"})
    assert abs(r["after"][0]["stats"]["skewness"]) < abs(r["before"]["stats"]["skewness"])

def test_preview_returns_updated_scaling_after_cap(): ...  # before: robust; after cap: standard
def test_preview_drop_rows_count(): ...
def test_preview_dropped_column_has_empty_after(): ...
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it.**  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(backend): before/after preview"`

---

### Task 14: Excel report and zip export

**Files:**
- Create: `backend/app/report.py`, `backend/tests/test_report.py`

**Interfaces:**
- Consumes: `SplitResult`, the findings, per-column stats, `ApplyResult`, `t`.
- Produces:
  - `build_report(meta: dict, split: SplitResult, stats: dict[str, dict], types: dict[str, str], findings: list[Finding], result: ApplyResult) -> bytes`. `meta` holds `filename, mode, target, sheet`.
  - `build_zip(result: ApplyResult, report_bytes: bytes) -> bytes` with the entries `train.csv`, `test.csv`, `report.xlsx`.

Sheets. All headers come from i18n keys `report.*`.
- **Dataset**, as label/value rows:
  - file, sheet, mode, target, task
  - rows (raw), duplicates removed, rows with missing target removed
  - split method (stratified/random), train size, test size, train rows dropped
  - warnings
  - class counts, ratio, imbalance recommendation
- **Features**, one row per non-target column:
  - column, type
  - stats: missing %, unique, mean, std, min, max, skewness, outlier %
  - anomalies: rule names joined with `; `
  - recommendations: `rule: option — reason`, joined with a line break
  - alternatives: `rule: opt1, opt2, …`
  - applied: `rule: option`
  - matches recommendation: `yes`, `no`, or `partial`

  For scaling, use the **recomputed** finding from `result.scaling_findings`.
- **Correlations**: column A, column B, r, dropped column (from the correlation findings and the choices).

- [ ] **Step 1: Write the failing tests**

```python
def test_report_sheets_and_feature_rows(applied_fixture):
    wb = openpyxl.load_workbook(io.BytesIO(build_report(...)))
    assert wb.sheetnames == ["Dataset", "Features", "Correlations"]
    rows = list(wb["Features"].iter_rows(values_only=True))
    assert len(rows) - 1 == n_non_target_columns
    assert any("median" in str(c) for c in rows[1])              # applied option visible

def test_report_matches_finding_numbers(applied_fixture): ...    # skewness cell == finding stats value
def test_zip_contains_three_files():
    names = zipfile.ZipFile(io.BytesIO(build_zip(result, b"x"))).namelist()
    assert sorted(names) == ["report.xlsx", "test.csv", "train.csv"]
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement it** with `pd.ExcelWriter(engine="openpyxl")`. Set the column widths and the wrap-text style on the reason columns.  **Step 4: Run the tests to verify they pass.**

- [ ] **Step 5: Commit.** `git commit -m "feat(backend): excel report and zip export"`

---

### Task 15: Session store and API routes

**Files:**
- Create: `backend/app/session.py`, `backend/app/main.py`, `backend/tests/test_api.py`

**Interfaces:**
- Produces:
  - `@dataclass Session(raw: pd.DataFrame, filename: str, sheet: str | None, sheets: list[str], types: dict, mode: str | None = None, target: str | None = None, split: SplitResult | None = None, findings: list[Finding] = [], stats: dict = {}, result: ApplyResult | None = None, choices: dict = {})`. Use field factories for the mutable defaults.
  - Store functions: `SESSIONS: dict[str, Session]`, `create(session) -> str` (uuid4 hex), `get(sid) -> Session`, which raises `HTTPException(404)`.
  - Routes. All JSON goes through `allow_nan=False`-safe dicts, and `CORSMiddleware` allows `http://localhost:5173`.

| Route | Request | Response |
|---|---|---|
| `GET /labels` | — | `ui_labels()` |
| `POST /upload` | multipart `file`, form `sheet?` | `{session_id, filename, sheets, sheet, columns, types, n_rows}`. 400 with the i18n message on `ValueError` |
| `POST /configure` | `{session_id, mode, target?, type_overrides?}` | `{task, stratified, n_train, n_test, n_duplicates, n_target_missing, warnings}`. 400 if supervised without a valid target |
| `GET /eda?session_id=` | — | `{columns: [{name, type, stats, chart}], correlation, dataset: {...same as configure}}`, computed on train |
| `GET /findings?session_id=` | — | `{findings: [Finding.to_dict()]}` |
| `POST /preview` | `{session_id, column, choices}` | `preview_column(...)` |
| `POST /apply` | `{session_id, choices}` (column → rule → option) | `{n_train, n_test, n_columns_out, rows_dropped_train, applied}` |
| `GET /export?session_id=` | — | zip download (`application/zip`, `Content-Disposition: attachment; filename=smart_cleaner_export.zip`). 409 if apply hasn't run |

- [ ] **Step 1: Write the failing end-to-end test** with `fastapi.testclient.TestClient`:

```python
def test_full_flow(mixed_df_csv_bytes):
    c = TestClient(app)
    up = c.post("/upload", files={"file": ("d.csv", mixed_df_csv_bytes)}).json()
    sid = up["session_id"]
    conf = c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "target"}).json()
    assert conf["stratified"] and conf["n_test"] > 0
    assert c.get("/eda", params={"session_id": sid}).status_code == 200
    fs = c.get("/findings", params={"session_id": sid}).json()["findings"]
    choices = {}
    for f in fs:
        if f["column"]: choices.setdefault(f["column"], {})[f["rule"]] = f["recommendation"]
    assert c.post("/preview", json={"session_id": sid, "column": "num", "choices": choices["num"]}).status_code == 200
    assert c.post("/apply", json={"session_id": sid, "choices": choices}).status_code == 200
    z = c.get("/export", params={"session_id": sid})
    assert z.headers["content-type"] == "application/zip"

def test_export_before_apply_409(): ...
def test_unknown_session_404(): ...
def test_supervised_without_target_400(): ...
def test_type_override_changes_findings(): ...   # override "pclass" to numeric -> gets scaling finding
def test_unreadable_upload_400(): ...
```

- [ ] **Step 2: Run them to verify they fail.**  **Step 3: Implement the session store and routes.**  **Step 4: Run the full suite.** Expected: all pass.

- [ ] **Step 5: Smoke-run the server.** Run `.venv/Scripts/python -m uvicorn app.main:app --reload` and open `http://localhost:8000/docs`. Expected: all routes listed.

- [ ] **Step 6: Commit.** `git commit -m "feat(api): session store and routes"`

---

### Task 16: Frontend scaffold, API client, choices state, Import tab

**Files:**
- Create: `frontend/` via `npm create vite@latest frontend -- --template react`, `frontend/src/api.js`, `frontend/src/choices.js`, `frontend/src/choices.test.js`, `frontend/src/LabelsContext.jsx`, `frontend/src/App.jsx`, `frontend/src/tabs/ImportTab.jsx`

**Interfaces:**
- Consumes: the API in Task 15.
- Produces:
  - `api.js`: `API = import.meta.env.VITE_API_URL ?? "http://localhost:8000"` and the functions `getLabels(), upload(file, sheet?), configure(body), getEda(sid), getFindings(sid), preview(body), apply(body), exportUrl(sid)`. All return parsed JSON and throw `Error(detail)` on non-2xx responses.
  - `choices.js`:
    - `defaultChoices(findings) -> {[column]: {[rule]: option}}` uses each recommendation and skips findings whose `column` is null.
    - `setChoice(choices, column, rule, option) -> newChoices` is immutable.
  - `useLabels()` hook. The `t(key)` helper returns `labels[key] ?? key`.
  - `App` holds `{sessionId, upload, config, eda, findings, choices, applied}` and the active tab. Tabs after Import stay disabled until configure succeeds.
  - Import tab:
    - file input
    - sheet select (shown when `sheets.length > 1`, re-uploads with the chosen sheet)
    - mode radio
    - target select (supervised only)
    - per-column type dropdown, prefilled with the inferred types and sent as `type_overrides`
    - "Analyse" button, which calls configure and then loads the EDA and the findings

- [ ] **Step 1: Scaffold the app and install dependencies.** Run (repo root): `npm create vite@latest frontend -- --template react`, then `cd frontend && npm install && npm install react-plotly.js plotly.js-dist-min && npm install -D vitest`. Add `"test": "vitest run"` to `package.json`. Expected: `npm run dev` serves on 5173.

- [ ] **Step 2: Write the failing test** (`choices.test.js`):

```js
test("defaultChoices uses recommendations and skips dataset findings", () => {
  const f = [{column: "a", rule: "missing", recommendation: "median"},
             {column: null, rule: "duplicates", recommendation: "remove"}];
  expect(defaultChoices(f)).toEqual({a: {missing: "median"}});
});
test("setChoice is immutable", () => {
  const c = {a: {missing: "median"}}; const n = setChoice(c, "a", "missing", "mean");
  expect(c.a.missing).toBe("median"); expect(n.a.missing).toBe("mean");
});
```

- [ ] **Step 3: Run it to verify it fails.** Run `npm test`. Expected: FAIL.

- [ ] **Step 4: Implement `choices.js`, `api.js`, `LabelsContext`, `App`, `ImportTab`.** Add every new label key to `backend/app/i18n.py` under `ui.`.

- [ ] **Step 5: Run the tests to verify they pass.** Run `npm test`. Expected: 2 passed.

- [ ] **Step 6: Manual check.** With the backend running, upload a small CSV, pick a target, and click Analyse. Expected: no console errors, and the EDA tab becomes enabled.

- [ ] **Step 7: Commit.** `git add frontend backend/app/i18n.py && git commit -m "feat(frontend): scaffold, api client, import tab"`. Make sure `frontend/node_modules` is ignored (the root `.gitignore` already covers it).

---

### Task 17: EDA tab

**Files:**
- Create: `frontend/src/tabs/EdaTab.jsx`, `frontend/src/components/Chart.jsx`

**Interfaces:**
- Consumes: the `GET /eda` response.
- Produces:
  - `<Chart chart={chartData} title />`, which renders a `histogram` as a Plotly bar chart (x = bin centres from the edges) and a `bar` as a Plotly bar chart. It's reused by Task 18.
  - The EDA tab shows:
    - a dataset banner: rows, duplicates removed, train/test sizes, split method, class ratio, warnings
    - a sortable stats table (type, missing %, unique, mean, std, min, max, skewness, outlier %); missing % > 0 is highlighted
    - a per-column chart grid
    - a correlation heatmap (Plotly `heatmap`)

- [ ] **Step 1: Implement it.** Plotly config is `{displaylogo: false, responsive: true}`.

- [ ] **Step 2: Manual check on Titanic.** Expected: the Age missing % shows ~20%, the Sex bar chart has 2 bars, and the heatmap covers the numeric columns only.

- [ ] **Step 3: Commit.** `git commit -m "feat(frontend): EDA tab"`

---

### Task 18: Preprocessing tab

**Files:**
- Create: `frontend/src/tabs/PreprocessingTab.jsx`, `frontend/src/components/ColumnCard.jsx`, `frontend/src/components/FindingRow.jsx`

**Interfaces:**
- Consumes: findings, `choices` and `setChoice`, `preview()`, `<Chart>`.
- Produces:
  - Dataset findings (duplicates, imbalance) appear in a banner above the cards.
  - **One card per non-target column**, including columns with no findings, which show "no anomaly detected". Each card shows:
    - a key-stats line
    - a `FindingRow` for each finding: rule name, severity colour, the recommendation and the reason text in full, and a radio group listing every alternative with its trade-off as helper text. The recommended option carries a "Recommended" tag.
    - a "Preview" button that calls `/preview` with that column's choices and shows the before and after `<Chart>` side by side with key stats. The scaling `FindingRow` shows the recomputed scaling recommendation that `/preview` returns.
  - "Reset to recommendations" resets the choices to `defaultChoices(findings)`.
  - The rule filter dropdown and the "only columns with warnings" toggle are optional. Skip them if time is short.

- [ ] **Step 1: Implement it.**

- [ ] **Step 2: Manual check on the fraud dataset.** Expected:
  - `Amount` shows skewness with log1p recommended, and the outlier signal rule says "none" with both fraud rates.
  - Preview with log1p shows a less skewed histogram.
  - Switching the outlier choice to cap and previewing again updates the scaling recommendation.

- [ ] **Step 3: Commit.** `git commit -m "feat(frontend): preprocessing tab with preview"`

---

### Task 19: Export tab

**Files:**
- Create: `frontend/src/tabs/ExportTab.jsx`

**Interfaces:**
- Consumes: `apply()` and `exportUrl()`.
- Produces:
  - A summary of the choices: counts of recommended vs. changed vs. `none`, and the columns that will be dropped.
  - An "Apply transformations" button that calls `/apply` and shows `n_train, n_test, n_columns_out, rows_dropped_train`.
  - A "Download zip" link (`href = exportUrl(sid)`), enabled only after apply.
  - A note explaining that the transformers are fitted on train only.

- [ ] **Step 1: Implement it.**

- [ ] **Step 2: Manual check.** Apply on Titanic, download the zip, and open `report.xlsx`. Expected: 3 sheets, one Features row per column, and an "applied" column that matches the choices.

- [ ] **Step 3: Commit.** `git commit -m "feat(frontend): export tab"`

---

### Task 20: Validation datasets, README, CLAUDE.md commands

**Files:**
- Create: `README.md`, `backend/tests/test_datasets.py`, `backend/tests/fixtures/multisheet.xlsx` (built by a fixture-builder function in the test, not committed binary-first)
- Modify: `CLAUDE.md` (replace the "Project status" placeholder with the real commands)

**Interfaces:**
- Consumes: everything.

- [ ] **Step 1: Write the generality tests** (no network, using scikit-learn's bundled data):

```python
@pytest.mark.parametrize("loader,task", [(load_iris, "classification"), (load_wine, "classification"),
                                         (load_diabetes, "regression")])
def test_sklearn_datasets_full_flow(loader, task):
    df = loader(as_frame=True).frame
    # upload via TestClient as CSV, configure supervised target="target", apply recommendations, export
    assert conf["task"] == task and export.status_code == 200

def test_multisheet_with_text_and_bad_dates(tmp_path):
    # sheet "notes" with free-text column (60 long sentences) + messy date column (60% parse) + numeric
    # upload sheet="notes" -> findings include free_text and datetime warning; apply + export succeed
```

`load_diabetes` replaces California housing because it ships offline with scikit-learn. It covers the same regression case.

- [ ] **Step 2: Run them.** Run `.venv/Scripts/python -m pytest tests/test_datasets.py -q`. Expected: pass. Fix any failures in the owning module and re-run the full suite.

- [ ] **Step 3: Manual demo rehearsal.** Put `creditcard.csv` and `titanic.csv` in `data/` and run the full flow in the browser for each. Time the fraud upload, EDA and apply steps (each should take under ~15 s on the laptop). Note any slow step and fix it by sampling chart inputs only. Statistics stay on the full train data.

- [ ] **Step 4: Write `README.md`**, with:
  - the purpose
  - setup: backend venv plus `pip install -r requirements.txt`, frontend `npm install`
  - running: `uvicorn app.main:app --reload` from `backend/`, `npm run dev` from `frontend/`
  - the test commands
  - a "How recommendations work" section linking to spec §8
  - the export contents

  Update `CLAUDE.md`'s status section with the same commands, plus a one-test example: `.venv/Scripts/python -m pytest tests/test_rules_missing.py::test_skewed_numeric_gets_median -q`.

- [ ] **Step 5: Commit.** `git add -A && git commit -m "test: generality datasets; docs: README and CLAUDE.md commands"`
