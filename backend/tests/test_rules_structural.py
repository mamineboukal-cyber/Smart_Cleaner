import numpy as np
import pandas as pd

from app.rules.structural import check_constant, check_datetime, check_free_text, check_id_like
from tests.conftest import ctx_for


def test_constant_fires_at_99_pct():
    s = pd.Series([1] * 99 + [2])
    f = check_constant(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column" and f.stats["top_freq_pct"] == 99.0
    assert "99" in f.reason and {a.option for a in f.alternatives} == {"drop_column", "keep"}


def test_constant_fires_on_single_value():
    s = pd.Series(["a"] * 10)
    assert check_constant(s, ctx_for(s, "categorical")).recommendation == "drop_column"


def test_constant_not_fired_at_98_pct():
    s = pd.Series([1] * 98 + [2, 3])
    assert check_constant(s, ctx_for(s, "categorical")) is None


def test_id_like_fires_on_unique_ints():
    s = pd.Series(range(100))
    f = check_id_like(s, ctx_for(s, "numeric"))
    assert f.recommendation == "drop_column"
    assert {a.option for a in f.alternatives} == {"drop_column", "keep"}
    assert "95" in f.reason


def test_id_like_fires_on_unique_strings():
    s = pd.Series([f"user_{i}" for i in range(100)])
    assert check_id_like(s, ctx_for(s, "categorical")).recommendation == "drop_column"


def test_id_like_ignores_continuous_floats():
    s = pd.Series(np.random.default_rng(0).normal(size=100))
    assert check_id_like(s, ctx_for(s, "numeric")) is None


def test_free_text_fires_on_long_unique_strings():
    texts = [f"this is a fairly long sentence number {i:03d} ok" for i in range(60)]
    s = pd.Series(texts * 2)  # unique ratio 0.5, so not ID-like
    f = check_free_text(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column" and f.severity == "warning"
    assert {a.option for a in f.alternatives} == {"drop_column", "keep"}


def test_free_text_ignores_short_categories():
    s = pd.Series(["red", "green", "blue"] * 40)
    assert check_free_text(s, ctx_for(s, "categorical")) is None


def test_free_text_ignores_id_like_text():
    texts = [f"this is a fairly long sentence number {i:03d} ok" for i in range(100)]
    s = pd.Series(texts)
    assert check_free_text(s, ctx_for(s, "categorical")) is None


def test_datetime_extract():
    s = pd.Series(pd.date_range("2020-01-01", periods=10))
    f = check_datetime(s, ctx_for(s, "datetime"))
    assert f.recommendation == "extract"
    assert {a.option for a in f.alternatives} == {"extract", "drop_column", "keep"}


def test_inconsistent_dates_flagged():
    s = pd.Series(["2020-01-01"] * 6 + ["junk"] * 4)
    f = check_datetime(s, ctx_for(s, "categorical"))
    assert f.recommendation == "drop_column" and f.severity == "warning"
    assert {a.option for a in f.alternatives} == {"drop_column", "keep"}


def test_plain_categories_not_flagged_as_dates():
    s = pd.Series(["red", "green"] * 5)
    assert check_datetime(s, ctx_for(s, "categorical")) is None


def test_time_only_column_extracts_hour_and_minute():
    s = pd.Series(["14:32:05", "09:15:00", "23:59:59"] * 4)
    f = check_datetime(s, ctx_for(s, "datetime"))
    assert f.recommendation == "extract" and f.stats == {"time_only": True}
    assert "hour" in f.reason and "year" not in f.reason
    extract = next(a for a in f.alternatives if a.option == "extract")
    assert "hour" in extract.tradeoff and "year" not in extract.tradeoff
