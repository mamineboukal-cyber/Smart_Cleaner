import numpy as np
import pandas as pd

from app.rules.dataset import check_correlation, check_duplicates, check_imbalance

rng = np.random.default_rng(0)
X = rng.normal(size=200)
NOISE = rng.normal(size=200)
OTHER = rng.normal(size=200)


def test_duplicates_finding():
    f = check_duplicates(3, 100)
    assert f.column is None and f.recommendation == "remove" and f.stats["n_duplicates"] == 3
    assert [a.option for a in f.alternatives] == ["remove"]
    assert "split" in f.alternatives[0].tradeoff.lower()


def test_no_duplicates_no_finding():
    assert check_duplicates(0, 100) is None


def test_correlated_pair_drops_later_column():
    df = pd.DataFrame({"a": X, "b": X * 2 + 0.001 * NOISE, "c": OTHER})
    fs = check_correlation(df, ["a", "b", "c"], {"a": 0, "b": 0, "c": 0})
    assert len(fs) == 1 and fs[0].column == "b" and fs[0].stats["other"] == "a"
    assert fs[0].stats["r"] > 0.95 and fs[0].recommendation == "drop_column"
    assert {a.option for a in fs[0].alternatives} == {"drop_column", "keep"}


def test_correlated_pair_drops_more_missing():
    df = pd.DataFrame({"a": X, "b": X * 2 + 0.001 * NOISE})
    fs = check_correlation(df, ["a", "b"], {"a": 10.0, "b": 0.0})
    assert fs[0].column == "a" and fs[0].stats["other"] == "b"


def test_negative_correlation_counts():
    df = pd.DataFrame({"a": X, "b": -X})
    assert len(check_correlation(df, ["a", "b"], {"a": 0, "b": 0})) == 1


def test_uncorrelated_no_findings():
    df = pd.DataFrame({"a": X, "c": OTHER})
    assert check_correlation(df, ["a", "c"], {"a": 0, "c": 0}) == []


def test_imbalance_binary():
    y = pd.Series([1] * 5 + [0] * 95, name="fraud")
    f = check_imbalance(y)
    assert f.column == "fraud" and f.recommendation == "class_weight_balanced"
    assert abs(f.stats["ratio"] - 5 / 95) < 1e-3 and f.stats["smallest_class"] == "1"
    assert {a.option for a in f.alternatives} == {"class_weight_balanced", "none"}


def test_imbalance_multiclass_ratio():
    y = pd.Series(["a"] * 100 + ["b"] * 100 + ["c"] * 15, name="y")
    f = check_imbalance(y)
    assert f.stats["ratio"] == 0.15 and f.recommendation == "class_weight_balanced"


def test_balanced_multiclass_reports_none():
    y = pd.Series(list("abcde") * 20, name="y")
    f = check_imbalance(y)
    assert f.recommendation == "none" and f.stats["ratio"] == 1.0
    assert isinstance(f.stats["class_counts"], str)
