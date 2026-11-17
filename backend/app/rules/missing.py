"""Spec §8 rules 4, 5 and 5b: missing values."""

import pandas as pd

from app.findings import (
    CONSTANT_FILL, CONSTANT_MISSING, DROP_COLUMN, DROP_ROWS, MEAN, MEDIAN, MISSING, MODE, NONE,
    Finding,
)
from app.i18n import t
from app.rules.context import alternatives

MISSING_DROP_PCT = 50   # > 50% missing -> drop the column
SKEW_THRESHOLD = 1      # |skew| > 1 -> median instead of mean

NUMERIC_OPTIONS = (MEAN, MEDIAN, CONSTANT_FILL, DROP_ROWS, DROP_COLUMN, NONE)
CATEGORICAL_OPTIONS = (MODE, CONSTANT_MISSING, DROP_ROWS, DROP_COLUMN, NONE)


def _ordered(first: str, options: tuple[str, ...]) -> tuple[str, ...]:
    """Recommendation first, then the other options in their usual order."""
    return (first, *[o for o in options if o != first])


def check_missing(s: pd.Series, ctx) -> Finding | None:
    pct = ctx.stats["missing_pct"]
    if not pct:
        return None
    numeric = ctx.col_type == "numeric"
    options = NUMERIC_OPTIONS if numeric else CATEGORICAL_OPTIONS
    skewness = ctx.stats.get("skewness")
    stats = {"missing_pct": pct}

    if pct > MISSING_DROP_PCT:
        rec = DROP_COLUMN
        reason = t("reason.missing.drop_column", missing_pct=pct, threshold=MISSING_DROP_PCT)
    elif numeric:
        stats["skewness"] = skewness
        abs_skew = abs(skewness) if skewness is not None else 0.0
        rec = MEDIAN if abs_skew > SKEW_THRESHOLD else MEAN
        reason = t(f"reason.missing.{rec}", missing_pct=pct, abs_skew=round(abs_skew, 3),
                   threshold=SKEW_THRESHOLD)
    else:
        rec = MODE
        reason = t("reason.missing.mode", missing_pct=pct)

    return Finding(str(s.name), MISSING, stats, rec, reason, alternatives(*_ordered(rec, options)),
                   severity="warning" if rec == DROP_COLUMN else "info")
