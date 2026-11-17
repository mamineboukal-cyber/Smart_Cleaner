"""Spec §8 rules 6 (outliers, IQR) and 7 (skewness). Numeric columns only."""

import pandas as pd

from app.findings import (
    CAP, DROP_ROWS, LOG1P, NONE, OUTLIERS, SKEWNESS, SQRT, YEO_JOHNSON, Finding, round_stat,
)
from app.i18n import t
from app.rules.context import alternatives

CAP_MAX_PCT = 5          # <= 5% outliers -> cap; above, the tail is real (robust scaling)
SIGNAL_RATIO = 2         # minority-class rate among outliers >= 2x overall -> outliers are signal
SKEW_THRESHOLD = 1       # |skew| > 1 is "highly skewed"


def _outlier_mask(s: pd.Series, ctx) -> pd.Series | None:
    lo, hi = ctx.stats.get("lower_fence"), ctx.stats.get("upper_fence")
    if lo is None or hi is None:
        return None
    values = pd.to_numeric(s, errors="coerce")
    return (values < lo) | (values > hi)   # NaN compares False -> not an outlier


def outlier_target_rates(s: pd.Series, ctx) -> tuple[float, float] | None:
    """(% of the smallest class among outlier rows, % overall), or None if not classification."""
    if ctx.task != "classification" or ctx.target is None:
        return None
    mask = _outlier_mask(s, ctx)
    if mask is None or not mask.any():
        return None
    y = ctx.target.reindex(s.index)
    counts = y.value_counts()
    if counts.empty:
        return None
    minority = counts.idxmin()
    is_minority = y == minority
    in_outliers = is_minority[mask & y.notna()].mean() * 100
    overall = is_minority[y.notna()].mean() * 100
    return round_stat(in_outliers), round_stat(overall)


def check_outliers(s: pd.Series, ctx) -> Finding | None:
    if ctx.col_type != "numeric":
        return None
    pct = ctx.stats.get("outlier_pct") or 0
    if pct <= 0:
        return None
    st = ctx.stats
    stats = {"outlier_pct": pct, "q1": st["q1"], "q3": st["q3"],
             "lower_fence": st["lower_fence"], "upper_fence": st["upper_fence"]}
    rates = outlier_target_rates(s, ctx)
    if rates is not None:
        stats["outlier_target_rate"], stats["overall_target_rate"] = rates

    if rates is not None and rates[1] > 0 and rates[0] >= SIGNAL_RATIO * rates[1]:
        rec = NONE
        reason = t("reason.outliers.signal", outlier_rate=rates[0], overall_rate=rates[1], ratio=SIGNAL_RATIO)
    elif pct <= CAP_MAX_PCT:
        rec = CAP
        reason = t("reason.outliers.cap", outlier_pct=pct, threshold=CAP_MAX_PCT,
                   lower=st["lower_fence"], upper=st["upper_fence"])
    else:
        rec = NONE
        reason = t("reason.outliers.heavy_tail", outlier_pct=pct, threshold=CAP_MAX_PCT)

    options = [rec] + [o for o in (CAP, DROP_ROWS, NONE) if o != rec]
    return Finding(str(s.name), OUTLIERS, stats, rec, reason, alternatives(*options), severity="warning")


def check_skewness(s: pd.Series, ctx) -> Finding | None:
    if ctx.col_type != "numeric":
        return None
    skewness, minimum = ctx.stats.get("skewness"), ctx.stats.get("min")
    if skewness is None or abs(skewness) <= SKEW_THRESHOLD:
        return None
    stats = {"skewness": skewness, "min": minimum}
    if minimum is not None and minimum >= 0:
        rec, options = LOG1P, (LOG1P, YEO_JOHNSON, SQRT, NONE)
    else:
        rec, options = YEO_JOHNSON, (YEO_JOHNSON, NONE)
    reason = t(f"reason.skewness.{rec}", skewness=skewness, threshold=SKEW_THRESHOLD, min=minimum)
    return Finding(str(s.name), SKEWNESS, stats, rec, reason, alternatives(*options))
