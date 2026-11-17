"""Dataset-level rules: spec §8 rules 1 (duplicates), 10 (correlation), 12 (imbalance)."""

import pandas as pd

from app.findings import (
    CLASS_WEIGHT_BALANCED, CORRELATION, DROP_COLUMN, DUPLICATES, IMBALANCE, KEEP, NONE, REMOVE,
    Finding, round_stat,
)
from app.i18n import t
from app.rules.context import alternatives

CORRELATION_MAX = 0.95   # |Pearson r| > 0.95 -> near-duplicate information
IMBALANCE_RATIO = 0.2    # smallest / largest class < 0.2 -> class weights


def check_duplicates(n_duplicates: int, n_rows_raw: int) -> Finding | None:
    """Duplicates were already removed before the split; this records it."""
    if not n_duplicates:
        return None
    pct = round_stat(n_duplicates / n_rows_raw * 100) if n_rows_raw else 0.0
    stats = {"n_duplicates": int(n_duplicates), "n_rows_raw": int(n_rows_raw), "duplicate_pct": pct}
    reason = t("reason.duplicates.remove", n_duplicates=n_duplicates, duplicate_pct=pct)
    return Finding(None, DUPLICATES, stats, REMOVE, reason, alternatives(REMOVE), severity="warning")


def check_correlation(train: pd.DataFrame, numeric_cols: list[str],
                      missing_pct: dict[str, float]) -> list[Finding]:
    """One finding per pair with |r| > 0.95; the column to drop is the one with
    more missing values, or the later one in ``numeric_cols`` on a tie."""
    if len(numeric_cols) < 2:
        return []
    corr = train[numeric_cols].apply(pd.to_numeric, errors="coerce").corr(method="pearson")
    findings = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1:]:
            r = corr.loc[a, b]
            if pd.isna(r) or abs(r) <= CORRELATION_MAX:
                continue
            drop, keep = (a, b) if (missing_pct.get(a) or 0) > (missing_pct.get(b) or 0) else (b, a)
            r = round_stat(r)
            reason = t("reason.correlation.drop_column", drop=drop, keep=keep, r=r, threshold=CORRELATION_MAX)
            findings.append(Finding(drop, CORRELATION, {"other": keep, "r": r}, DROP_COLUMN, reason,
                                    alternatives(DROP_COLUMN, KEEP), severity="warning"))
    return findings


def check_imbalance(y_train: pd.Series) -> Finding | None:
    """Classification targets only (the caller checks the task). Always reports the ratio."""
    counts = y_train.dropna().value_counts()
    if counts.empty:
        return None
    ratio = round_stat(counts.min() / counts.max())
    smallest = str(counts.idxmin())
    stats = {
        "class_counts": ", ".join(f"{k}: {v}" for k, v in counts.items()),
        "ratio": ratio,
        "smallest_class": smallest,
    }
    rec = CLASS_WEIGHT_BALANCED if ratio < IMBALANCE_RATIO else NONE
    reason = t(f"reason.imbalance.{rec}", ratio=ratio, smallest=smallest, threshold=IMBALANCE_RATIO)
    return Finding(str(y_train.name), IMBALANCE, stats, rec, reason,
                   alternatives(CLASS_WEIGHT_BALANCED, NONE),
                   severity="warning" if rec == CLASS_WEIGHT_BALANCED else "info")
