import numpy as np
import pandas as pd

from app.i18n import t
from app.rules.missing import check_missing
from tests.conftest import ctx_for

NUMERIC_OPTIONS = {"median", "mean", "constant", "drop_rows", "drop_column", "none"}


def test_no_missing_no_finding():
    s = pd.Series([1.0, 2.0, 3.0])
    assert check_missing(s, ctx_for(s, "numeric")) is None


def test_over_50_pct_drops_column():
    s = pd.Series([1.0, 2.0, 3.0, 4.0] + [np.nan] * 6)
    f = check_missing(s, ctx_for(s, "numeric"))
    assert f.recommendation == "drop_column" and f.stats["missing_pct"] == 60.0
    assert "60" in f.reason
    assert {a.option for a in f.alternatives} == NUMERIC_OPTIONS


def test_over_50_pct_categorical_alternatives():
    s = pd.Series(["a", "b"] + [None] * 3)
    f = check_missing(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column"
    assert {a.option for a in f.alternatives} == {"drop_column", "mode", "constant_missing", "drop_rows", "none"}


def test_skewed_numeric_gets_median():
    s = pd.Series(list(np.random.default_rng(0).exponential(size=90)) + [np.nan] * 10)
    f = check_missing(s, ctx_for(s, "numeric"))
    assert f.recommendation == "median" and abs(f.stats["skewness"]) > 1
    assert {a.option for a in f.alternatives} == NUMERIC_OPTIONS


def test_symmetric_numeric_gets_mean():
    s = pd.Series(list(np.random.default_rng(0).normal(size=90)) + [np.nan] * 10)
    f = check_missing(s, ctx_for(s, "numeric"))
    assert f.recommendation == "mean"


def test_categorical_gets_mode_with_missing_alternative():
    s = pd.Series(["a", "b", "a", None])
    f = check_missing(s, ctx_for(s, "categorical"))
    assert f.recommendation == "mode"
    assert {a.option for a in f.alternatives} == {"mode", "constant_missing", "drop_rows", "drop_column", "none"}


def test_drop_rows_tradeoff_says_train_only():
    assert "train" in t("tradeoff.drop_rows").lower()
