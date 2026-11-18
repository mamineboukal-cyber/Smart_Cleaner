"""Per-column statistics and chart data.

Chart payloads are bounded (<= 30 histogram bins, <= 20 bars) so the response
size does not grow with the number of rows (285k for the fraud dataset).

Two cases get no top-values bar chart, because it would be empty to the eye
(each top value covers a handful of rows next to a huge "Other" bar):
time-of-day columns are charted as rows per hour instead, and other columns
where almost every value is unique get a short note ("kind": "unique").
"""

import numpy as np
import pandas as pd
from scipy.stats import skew

from app.findings import round_stat
from app.i18n import t
from app.rules.structural import ID_UNIQUE_RATIO
from app.types import is_time_only, to_datetime

IQR_FACTOR = 1.5   # Tukey fences
MAX_BINS = 30
MAX_BARS = 20


def iqr_fences(values: pd.Series) -> tuple[float, float, float, float]:
    """Return q1, q3, lower fence, upper fence (Tukey 1.5 * IQR)."""
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr = q3 - q1
    return q1, q3, q1 - IQR_FACTOR * iqr, q3 + IQR_FACTOR * iqr


def column_stats(s: pd.Series, col_type: str) -> dict:
    """Statistics for one column. Every value is JSON-safe (NaN -> None).
    Percentages are on a 0-100 scale."""
    n = len(s)
    non_null = s.dropna()
    n_unique = int(non_null.nunique())
    top_freq = non_null.value_counts().iloc[0] / n * 100 if n_unique else 0.0
    st = {
        "count": n,
        "missing_pct": round_stat(s.isna().mean() * 100 if n else 0.0),
        "n_unique": n_unique,
        "unique_ratio": round_stat(n_unique / len(non_null) if len(non_null) else 0.0),
        "top_freq_pct": round_stat(top_freq),
    }
    if col_type == "numeric":
        values = pd.to_numeric(non_null, errors="coerce").dropna().astype(float)
        if values.empty:
            for key in ("mean", "std", "min", "max", "skewness", "q1", "q3", "lower_fence", "upper_fence"):
                st[key] = None
            st["outlier_pct"] = 0.0
            return st
        q1, q3, lo, hi = iqr_fences(values)
        outliers = ((values < lo) | (values > hi)).sum()
        st.update({
            "mean": round_stat(values.mean()),
            "std": round_stat(values.std()),
            "min": round_stat(values.min()),
            "max": round_stat(values.max()),
            "skewness": round_stat(skew(values, bias=False)) if len(values) >= 3 and values.nunique() > 1 else None,
            "q1": round_stat(q1),
            "q3": round_stat(q3),
            "lower_fence": round_stat(lo),
            "upper_fence": round_stat(hi),
            "outlier_pct": round_stat(outliers / len(values) * 100),
        })
    else:
        st["mean_length"] = round_stat(non_null.astype(str).str.len().mean()) if len(non_null) else 0.0
    return st


def chart_data(s: pd.Series, col_type: str) -> dict:
    """Histogram (numeric) or top-categories bar chart (anything else)."""
    if col_type == "numeric":
        values = pd.to_numeric(s, errors="coerce").dropna().astype(float).to_numpy()
        if values.size == 0:
            return {"kind": "histogram", "edges": [], "counts": []}
        bins = min(MAX_BINS, max(1, int(np.unique(values).size)))
        counts, edges = np.histogram(values, bins=bins)
        return {"kind": "histogram", "edges": [round_stat(e) for e in edges], "counts": counts.tolist()}
    if col_type == "datetime" and is_time_only(s):
        hours = to_datetime(s).dt.hour.dropna().to_numpy()
        counts, _ = np.histogram(hours, bins=24, range=(0, 24))
        return {"kind": "histogram", "edges": list(range(25)), "counts": counts.tolist(),
                "x_label": t("ui.chart.hour_of_day")}
    vc = s.dropna().astype(str).value_counts()
    n_non_null = int(vc.sum())
    if len(vc) > MAX_BARS and len(vc) / n_non_null >= ID_UNIQUE_RATIO:
        return {"kind": "unique", "n_unique": len(vc), "unique_pct": round_stat(len(vc) / n_non_null * 100)}
    if len(vc) > MAX_BARS:
        top = vc.iloc[: MAX_BARS - 1]
        labels = top.index.tolist() + [t("ui.other")]
        counts = top.tolist() + [int(vc.iloc[MAX_BARS - 1 :].sum())]
    else:
        labels, counts = vc.index.tolist(), vc.tolist()
    return {"kind": "bar", "labels": labels, "counts": [int(c) for c in counts]}


def correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> dict:
    """Pearson correlation between numeric columns (NaN -> None)."""
    if not numeric_cols:
        return {"columns": [], "matrix": []}
    corr = df[numeric_cols].apply(pd.to_numeric, errors="coerce").corr(method="pearson")
    return {
        "columns": list(numeric_cols),
        "matrix": [[round_stat(v) for v in row] for row in corr.to_numpy()],
    }
