"""Fitting and applying the chosen transformations, column by column.

Leakage rule: every parameter (median, fences, lambda, categories, mean/std...)
is learned in ``fit`` from the TRAIN column only, then reused unchanged in
``transform`` for train and test alike.

Step order per column (spec §8):
  1 drop  2 datetime  3 missing  4 outliers  5 skewness  6 encoding  7 scaling
Each step is fitted on the train values produced by the steps before it.
"""

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.preprocessing import PowerTransformer

from app.findings import (
    CAP, CONSTANT_FILL, ENCODING, FREQUENCY, MINMAX, ONEHOT, ORDINAL, ROBUST, SCALING, STANDARD, CONSTANT_MISSING, DATETIME, DROP_COLUMN, DROP_ROWS, EXTRACT, KEEP, LOG1P,
    MEAN, MEDIAN, MISSING, MODE, NONE, OUTLIERS, SKEWNESS, SQRT, YEO_JOHNSON,
)
from app.findings import Finding
from app.profiling import column_stats, iqr_fences
from app.rules.context import ColumnContext
from app.rules.encoding import check_scaling
from app.split import SplitResult

MISSING_LABEL = "Missing"
# output suffix -> pandas .dt accessor
DATE_PARTS = {"year": "year", "month": "month", "day": "day", "dayofweek": "day_of_week"}
NO_OP = (NONE, KEEP)
PRE_STEPS = (MISSING, OUTLIERS, SKEWNESS)   # steps 3-5


def _to_datetime(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(s, errors="coerce", format="mixed")


class ColumnPipeline:
    def __init__(self, column: str, col_type: str, choices: dict[str, str]):
        self.column = column
        self.col_type = col_type
        self.choices = {rule: opt for rule, opt in choices.items() if opt not in NO_OP}
        self.params: dict = {}   # fitted values (JSON-friendly), for inspection and tests
        self._power: PowerTransformer | None = None
        self._applied: dict[str, str] = {}

    # ---------- public API ----------
    @property
    def dropped(self) -> bool:
        return DROP_COLUMN in self.choices.values()

    @property
    def numeric(self) -> bool:
        return self.col_type == "numeric"

    @property
    def extracts_dates(self) -> bool:
        return self.choices.get(DATETIME) == EXTRACT

    def applied(self) -> dict[str, str]:
        """Options actually applied (for the report), in step order."""
        return dict(self._applied)

    def fit(self, train: pd.DataFrame) -> "ColumnPipeline":
        self.params, self._applied = {}, {}
        if self.dropped:
            self._applied = {r: o for r, o in self.choices.items() if o == DROP_COLUMN}
            return self
        if self.extracts_dates:
            self._fit_datetime(train[self.column])
            return self   # the parts are complete integers: later steps don't apply
        s = self._coerce(train[self.column])
        for rule, fit_step in ((MISSING, self._fit_missing), (OUTLIERS, self._fit_outliers),
                               (SKEWNESS, self._fit_skewness)):
            if rule in self.choices and fit_step(s):
                self._applied[rule] = self.choices[rule]
                if rule == OUTLIERS and self.choices[rule] == DROP_ROWS:
                    s = s[self._outside_fences(s)]   # later steps fit on the rows train keeps
                s = self._apply_step(rule, s)
        self._fit_post(s)
        return self

    def transform(self, df: pd.DataFrame, is_train: bool) -> pd.DataFrame:
        """Output column(s) for this column, same index as ``df``. Never removes rows:
        the caller removes ``train_rows_to_drop`` from train beforehand, so train and
        test go through exactly the same fitted steps (``is_train`` is informative)."""
        if self.dropped:
            return pd.DataFrame(index=df.index)
        s = df[self.column]
        if self.extracts_dates:
            return self._transform_datetime(s)
        s = self._pre(self._coerce(s))
        return self._transform_post(s)

    def train_rows_to_drop(self, train: pd.DataFrame) -> pd.Index:
        """Train index labels removed by ``drop_rows`` (missing values or outliers)."""
        if self.dropped or self.extracts_dates:
            return pd.Index([])
        s = self._coerce(train[self.column])
        rows = pd.Index([])
        if self._applied.get(MISSING) == DROP_ROWS:
            rows = rows.union(s.index[s.isna()])
        if self._applied.get(OUTLIERS) == DROP_ROWS:
            if MISSING in self._applied:
                s = self._apply_step(MISSING, s)
            rows = rows.union(s.index[~self._outside_fences(s)])
        return rows

    def pre_scaling(self, df: pd.DataFrame) -> pd.Series | None:
        """The column after steps 3-5 (what scaling is fitted on), or None if the
        column is dropped or turned into date parts."""
        if self.dropped or self.extracts_dates:
            return None
        return self._pre(self._coerce(df[self.column]))

    # ---------- steps 6-7: encoding (categorical) and scaling (numeric) ----------
    def _fit_post(self, s: pd.Series) -> None:
        opt = self.choices.get(ENCODING)
        if not self.numeric and opt in (ONEHOT, ORDINAL, FREQUENCY):
            non_null = s.dropna()
            categories = sorted(non_null.unique().tolist(), key=str)
            if opt == FREQUENCY:
                freq = non_null.value_counts(normalize=True)
                self.params[ENCODING] = {"frequencies": {k: float(v) for k, v in freq.items()}}
            else:
                self.params[ENCODING] = {"categories": categories}
            self._applied[ENCODING] = opt
        opt = self.choices.get(SCALING)
        values = s.dropna()
        if self.numeric and opt in (STANDARD, MINMAX, ROBUST) and not values.empty:
            if opt == STANDARD:
                center, scale = values.mean(), values.std(ddof=0)
            elif opt == MINMAX:
                center, scale = values.min(), values.max() - values.min()
            else:
                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                center, scale = values.median(), q3 - q1
            if not scale or not np.isfinite(scale):
                scale = 1.0   # constant train column: avoid dividing by zero
            self.params[SCALING] = {"center": float(center), "scale": float(scale)}
            self._applied[SCALING] = opt

    def _transform_post(self, s: pd.Series) -> pd.DataFrame:
        opt = self._applied.get(ENCODING)
        if opt == ONEHOT:
            cats = self.params[ENCODING]["categories"]
            return pd.DataFrame({f"{self.column}_{c}": (s == c).astype("int64") for c in cats}, index=s.index)
        if opt == ORDINAL:
            codes = {c: i for i, c in enumerate(self.params[ENCODING]["categories"])}
            return s.map(codes).fillna(-1).astype("int64").to_frame(self.column)
        if opt == FREQUENCY:
            return s.map(self.params[ENCODING]["frequencies"]).fillna(0.0).astype(float).to_frame(self.column)
        if SCALING in self._applied:
            p = self.params[SCALING]
            s = (s - p["center"]) / p["scale"]
        return s.to_frame(self.column)

    # ---------- helpers ----------
    def _coerce(self, s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").astype(float) if self.numeric else s

    def _pre(self, s: pd.Series) -> pd.Series:
        """Steps 3-5 with the fitted parameters."""
        for rule in PRE_STEPS:
            if rule in self._applied:
                s = self._apply_step(rule, s)
        return s

    def _outside_fences(self, s: pd.Series) -> pd.Series:
        """True for rows kept (inside the fences or NaN)."""
        p = self.params[OUTLIERS]
        return ~((s < p["lower"]) | (s > p["upper"]))

    # ----- datetime (step 2) -----
    def _fit_datetime(self, s: pd.Series) -> None:
        d = _to_datetime(s)
        fill = {}
        for part, attr in DATE_PARTS.items():
            med = getattr(d.dt, attr).median()
            fill[part] = int(round(med)) if pd.notna(med) else 0
        self.params[DATETIME] = {"fill": fill}
        self._applied[DATETIME] = EXTRACT

    def _transform_datetime(self, s: pd.Series) -> pd.DataFrame:
        d = _to_datetime(s)
        fill = self.params[DATETIME]["fill"]
        return pd.DataFrame(
            {f"{self.column}_{p}": getattr(d.dt, attr).fillna(fill[p]).astype("int64") for p, attr in DATE_PARTS.items()},
            index=s.index,
        )

    # ----- missing (step 3) -----
    def _fit_missing(self, s: pd.Series) -> bool:
        opt = self.choices[MISSING]
        non_null = s.dropna()
        if self.numeric and opt == MEAN:
            value = non_null.mean()
        elif self.numeric and opt in (MEDIAN, DROP_ROWS):   # drop_rows: test NaN -> train median
            value = non_null.median()
        elif opt == MODE or (opt == DROP_ROWS and not self.numeric):
            if non_null.empty:
                value = 0.0 if self.numeric else MISSING_LABEL
            else:
                value = non_null.mode().iloc[0]
        elif opt == CONSTANT_FILL:
            value = 0.0 if self.numeric else MISSING_LABEL
        elif opt == CONSTANT_MISSING and not self.numeric:
            value = MISSING_LABEL
        else:
            return False   # option not valid for this column type: not applied
        if self.numeric and pd.isna(value):
            value = 0.0    # all-missing train column
        self.params[MISSING] = {"fill": value.item() if hasattr(value, "item") else value}
        return True

    # ----- outliers (step 4) -----
    def _fit_outliers(self, s: pd.Series) -> bool:
        values = s.dropna()
        if not self.numeric or self.choices[OUTLIERS] not in (CAP, DROP_ROWS) or values.empty:
            return False
        _, _, lo, hi = iqr_fences(values)   # exact fences (stats are rounded for display)
        self.params[OUTLIERS] = {"lower": float(lo), "upper": float(hi)}
        return True

    # ----- skewness (step 5) -----
    def _fit_skewness(self, s: pd.Series) -> bool:
        opt = self.choices[SKEWNESS]
        values = s.dropna()
        if not self.numeric or values.empty:
            return False
        if opt in (LOG1P, SQRT):
            # clip to the train min, and never below 0, so unseen test values stay finite
            self.params[SKEWNESS] = {"min": max(float(values.min()), 0.0)}
        elif opt == YEO_JOHNSON:
            pt = PowerTransformer(method="yeo-johnson", standardize=False)
            pt.fit(values.to_numpy().reshape(-1, 1))
            self._power = pt
            self.params[SKEWNESS] = {"lambda": float(pt.lambdas_[0])}
        else:
            return False
        return True

    def _apply_step(self, rule: str, s: pd.Series) -> pd.Series:
        p = self.params[rule]
        if rule == MISSING:
            return s.fillna(p["fill"])
        if rule == OUTLIERS:
            return s.clip(p["lower"], p["upper"])   # the test side of drop_rows is capped
        opt = self.choices[SKEWNESS]
        if opt == LOG1P:
            return np.log1p(s.clip(lower=p["min"]))
        if opt == SQRT:
            return np.sqrt(s.clip(lower=p["min"]))
        out = s.copy()
        mask = s.notna()
        if mask.any():
            out[mask] = self._power.transform(s[mask].to_numpy().reshape(-1, 1)).ravel()
        return out


@dataclass
class ApplyResult:
    train: pd.DataFrame
    test: pd.DataFrame
    applied: dict[str, dict[str, str]]           # column -> {rule: option actually applied}
    scaling_findings: dict[str, Finding] = field(default_factory=dict)
    rows_dropped_train: int = 0


def apply_all(split: SplitResult, types: dict[str, str], choices: dict[str, dict[str, str]],
              target: str | None) -> ApplyResult:
    """Fit every column on train, drop the chosen train rows, transform train and test."""
    columns = [str(c) for c in split.train.columns if c != target]
    pipelines = {c: ColumnPipeline(c, types[c], choices.get(c, {})).fit(split.train) for c in columns}

    to_drop = pd.Index([])
    for p in pipelines.values():
        to_drop = to_drop.union(p.train_rows_to_drop(split.train))
    train = split.train.drop(index=to_drop)

    def build(df: pd.DataFrame, is_train: bool) -> pd.DataFrame:
        parts = [p.transform(df, is_train) for p in pipelines.values()]
        out = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=df.index)
        if target is not None:
            out[target] = df[target]
        return out

    scaling_findings = {}
    for c, p in pipelines.items():
        if types[c] != "numeric":
            continue
        s = p.pre_scaling(train)
        if s is not None:
            ctx = ColumnContext("numeric", column_stats(s, "numeric"), None, split.task)
            scaling_findings[c] = check_scaling(s, ctx)

    return ApplyResult(
        train=build(train, True),
        test=build(split.test, False),
        applied={c: p.applied() for c, p in pipelines.items()},
        scaling_findings=scaling_findings,
        rows_dropped_train=len(to_drop),
    )
