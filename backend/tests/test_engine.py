import json

import numpy as np

from app import engine
from app.engine import run_rules
from app.split import prepare_and_split
from app.types import infer_types


def _run(df):
    return run_rules(prepare_and_split(df, "supervised", "target"), infer_types(df), "target")


def test_mixed_df_findings(mixed_df):
    findings, stats = _run(mixed_df)
    rules_by_col = {(f.column, f.rule) for f in findings}
    assert ("const_col", "constant") in rules_by_col and ("id_col", "id_like") in rules_by_col
    assert ("num", "missing") in rules_by_col and ("cat", "encoding") in rules_by_col
    assert ("target", "imbalance") in rules_by_col
    assert all(f.column != "target" or f.rule == "imbalance" for f in findings)
    assert "target" not in stats and stats["num"]["count"] == 160   # train rows only


def test_rule_order_per_column(mixed_df):
    findings, _ = _run(mixed_df)
    order = [f.rule for f in findings if f.column == "num"]
    assert order == sorted(order, key=engine.COLUMN_RULE_ORDER.index)


def test_all_missing_column_does_not_crash(mixed_df):
    df = mixed_df.assign(empty=np.nan)
    findings, _ = _run(df)
    f = next(f for f in findings if f.column == "empty" and f.rule == "missing")
    assert f.recommendation == "drop_column"
    json.dumps([f.to_dict() for f in findings], allow_nan=False)


def test_rule_exception_becomes_analysis_failed(monkeypatch, mixed_df):
    monkeypatch.setattr(engine, "check_skewness", lambda s, c: 1 / 0)
    findings, _ = _run(mixed_df)
    failed = [f for f in findings if f.rule == "analysis_failed"]
    assert failed and all(f.severity == "error" and f.recommendation == "none" for f in failed)
    assert "division by zero" in failed[0].reason
    assert any(f.rule == "encoding" for f in findings)   # the rest still ran


def test_unsupervised_has_no_imbalance(mixed_df):
    split = prepare_and_split(mixed_df, "unsupervised", None)
    findings, stats = run_rules(split, infer_types(mixed_df), None)
    assert not any(f.rule == "imbalance" for f in findings) and "target" in stats
