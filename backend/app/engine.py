"""Rule engine: runs every rule on the train split.

Never crash: each rule call is guarded. If a rule raises on a column, that
column gets an "analysis_failed" finding (default option "none") and the rest
of the dataset is still analysed.
"""

import pandas as pd

from app.findings import ANALYSIS_FAILED, NONE, Alternative, Finding
from app.i18n import t
from app.profiling import column_stats
from app.rules.context import ColumnContext
from app.rules.dataset import check_correlation, check_duplicates, check_imbalance
from app.rules.distribution import check_outliers, check_skewness
from app.rules.encoding import check_encoding, check_scaling
from app.rules.missing import check_missing
from app.rules.structural import check_constant, check_datetime, check_free_text, check_id_like
from app.split import SplitResult

# Spec §8 order. Names (not functions) so monkeypatching a check in tests works.
COLUMN_RULE_ORDER = [
    "constant", "id_like", "free_text", "datetime", "missing",
    "outliers", "skewness", "encoding", "scaling",
]


def _failed(column: str | None, error: Exception) -> Finding:
    return Finding(
        column, ANALYSIS_FAILED, {"error": str(error)}, NONE,
        t("reason.analysis_failed", error=str(error)),
        [Alternative(NONE, t("tradeoff.none"))], severity="error",
    )


def _guarded(findings: list[Finding], column: str | None, fn, *args) -> None:
    try:
        result = fn(*args)
    except Exception as e:  # noqa: BLE001 - by design: one bad rule must not stop the analysis
        findings.append(_failed(column, e))
        return
    if isinstance(result, Finding):
        findings.append(result)
    elif result:
        findings.extend(result)


def run_rules(split: SplitResult, types: dict[str, str], target: str | None
              ) -> tuple[list[Finding], dict[str, dict]]:
    """Return all findings and the per-column stats, both computed on train only."""
    train = split.train
    y = train[target] if target is not None else None
    findings: list[Finding] = []
    stats: dict[str, dict] = {}

    for col in train.columns:
        if col == target:
            continue
        name = str(col)
        s = train[col]
        try:
            stats[name] = column_stats(s, types[name])
        except Exception as e:  # noqa: BLE001
            findings.append(_failed(name, e))
            continue
        ctx = ColumnContext(types[name], stats[name], y, split.task)
        for rule in COLUMN_RULE_ORDER:
            _guarded(findings, name, globals()[f"check_{rule}"], s, ctx)

    _guarded(findings, None, check_duplicates, split.n_duplicates, split.n_rows_raw)
    numeric_cols = [c for c in stats if types[c] == "numeric"]
    missing = {c: stats[c]["missing_pct"] for c in stats}
    _guarded(findings, None, check_correlation, train, numeric_cols, missing)
    if split.task == "classification":
        _guarded(findings, str(target), check_imbalance, y)
    return findings, stats
