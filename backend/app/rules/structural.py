"""Structural rules: columns that should usually not be fed to a model as-is.

Spec §8 rules 2 (constant), 3 (ID-like), 11 (datetime) and 13 (free text).
"""

import pandas as pd

from app.findings import (
    CONSTANT, DATETIME, DROP_COLUMN, EXTRACT, FREE_TEXT, ID_LIKE, KEEP,
    Alternative, Finding,
)
from app.i18n import t
from app.rules.context import alternatives
from app.types import DATETIME_PARSE_MIN, date_parse_rate, is_time_only

CONSTANT_TOP_PCT = 99          # top value covers >= 99% of rows
ID_UNIQUE_RATIO = 0.95         # >= 95% of values are distinct
FREE_TEXT_MIN_UNIQUE = 50      # > 50 distinct values ...
FREE_TEXT_MIN_LENGTH = 30      # ... and mean length > 30 characters
DATE_FLAG_MIN = 0.50           # 50% <= parse rate < 90% -> "possible date"


def check_constant(s: pd.Series, ctx) -> Finding | None:
    st = ctx.stats
    if st["n_unique"] > 1 and st["top_freq_pct"] < CONSTANT_TOP_PCT:
        return None
    stats = {"n_unique": st["n_unique"], "top_freq_pct": st["top_freq_pct"]}
    reason = t("reason.constant.drop_column", n_unique=st["n_unique"],
               top_freq_pct=st["top_freq_pct"], threshold=CONSTANT_TOP_PCT)
    return Finding(str(s.name), CONSTANT, stats, DROP_COLUMN, reason, alternatives(DROP_COLUMN, KEEP))


def is_id_like(s: pd.Series, ctx) -> bool:
    eligible = ctx.col_type == "categorical" or (
        ctx.col_type == "numeric" and pd.api.types.is_integer_dtype(s)
    )
    return eligible and ctx.stats["unique_ratio"] >= ID_UNIQUE_RATIO


def check_id_like(s: pd.Series, ctx) -> Finding | None:
    if not is_id_like(s, ctx):
        return None
    ratio_pct = round(ctx.stats["unique_ratio"] * 100, 1)
    stats = {"unique_ratio": ctx.stats["unique_ratio"], "n_unique": ctx.stats["n_unique"]}
    reason = t("reason.id_like.drop_column", ratio_pct=ratio_pct, threshold=int(ID_UNIQUE_RATIO * 100))
    return Finding(str(s.name), ID_LIKE, stats, DROP_COLUMN, reason, alternatives(DROP_COLUMN, KEEP))


def check_free_text(s: pd.Series, ctx) -> Finding | None:
    st = ctx.stats
    if ctx.col_type != "categorical" or is_id_like(s, ctx):
        return None
    if st["n_unique"] <= FREE_TEXT_MIN_UNIQUE or (st.get("mean_length") or 0) <= FREE_TEXT_MIN_LENGTH:
        return None
    stats = {"n_unique": st["n_unique"], "mean_length": st["mean_length"]}
    reason = t("reason.free_text.drop_column", n_unique=st["n_unique"], mean_length=st["mean_length"],
               min_unique=FREE_TEXT_MIN_UNIQUE, min_length=FREE_TEXT_MIN_LENGTH)
    return Finding(str(s.name), FREE_TEXT, stats, DROP_COLUMN, reason,
                   alternatives(DROP_COLUMN, KEEP), severity="warning")


def check_datetime(s: pd.Series, ctx) -> Finding | None:
    if ctx.col_type == "datetime":
        if is_time_only(s):   # "14:32": hour and minute, not a meaningless year/month/day
            return Finding(str(s.name), DATETIME, {"time_only": True}, EXTRACT, t("reason.datetime.extract_time"),
                           [Alternative(EXTRACT, t("tradeoff.extract_time")), *alternatives(DROP_COLUMN, KEEP)])
        reason = t("reason.datetime.extract")
        return Finding(str(s.name), DATETIME, {}, EXTRACT, reason, alternatives(EXTRACT, DROP_COLUMN, KEEP))
    if ctx.col_type != "categorical" or pd.api.types.is_numeric_dtype(s):
        return None
    rate = date_parse_rate(s)
    if not DATE_FLAG_MIN <= rate < DATETIME_PARSE_MIN:
        return None
    rate_pct = round(rate * 100, 1)
    reason = t("reason.datetime.drop_column", parse_pct=rate_pct,
               low=int(DATE_FLAG_MIN * 100), high=int(DATETIME_PARSE_MIN * 100))
    return Finding(str(s.name), DATETIME, {"parse_rate_pct": rate_pct}, DROP_COLUMN, reason,
                   alternatives(DROP_COLUMN, KEEP), severity="warning")
