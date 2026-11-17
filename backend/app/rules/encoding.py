"""Spec §8 rules 8 (encoding, categorical) and 9 (scaling, numeric).

``check_scaling`` is also re-run on a column *after* its earlier steps
(imputation, capping, log...), with stats recomputed on the transformed
values, because those steps change the outlier share it decides on.
"""

import pandas as pd

from app.findings import (
    DROP_COLUMN, ENCODING, FREQUENCY, MINMAX, NONE, ONEHOT, ORDINAL, ROBUST, SCALING, STANDARD,
    Finding,
)
from app.i18n import t
from app.rules.context import alternatives

ONEHOT_MAX_CATEGORIES = 10   # beyond 10, one-hot adds too many sparse columns
ROBUST_MIN_OUTLIER_PCT = 5   # > 5% outliers -> RobustScaler


def check_encoding(s: pd.Series, ctx) -> Finding | None:
    if ctx.col_type != "categorical":
        return None
    n = ctx.stats["n_unique"]
    rec = ONEHOT if n <= ONEHOT_MAX_CATEGORIES else FREQUENCY
    reason = t(f"reason.encoding.{rec}", n_unique=n, threshold=ONEHOT_MAX_CATEGORIES)
    return Finding(str(s.name), ENCODING, {"n_unique": n}, rec, reason,
                   alternatives(ONEHOT, ORDINAL, FREQUENCY, DROP_COLUMN))


def check_scaling(s: pd.Series, ctx) -> Finding | None:
    if ctx.col_type != "numeric":
        return None
    pct = ctx.stats.get("outlier_pct") or 0
    rec = ROBUST if pct > ROBUST_MIN_OUTLIER_PCT else STANDARD
    reason = t(f"reason.scaling.{rec}", outlier_pct=pct, threshold=ROBUST_MIN_OUTLIER_PCT)
    return Finding(str(s.name), SCALING, {"outlier_pct": pct}, rec, reason,
                   alternatives(STANDARD, MINMAX, ROBUST, NONE))
