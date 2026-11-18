import json

import numpy as np
import pandas as pd

from app.findings import Alternative, Finding, round_stat
from app.profiling import chart_data, column_stats, correlation_matrix


def test_numeric_stats(numeric_series_with_outliers):
    st = column_stats(numeric_series_with_outliers, "numeric")
    assert st["missing_pct"] == 0
    # 20 of 1000 injected far outside the fences, plus ~0.7% natural normal-tail outliers
    assert 2.0 <= st["outlier_pct"] < 3.5
    assert st["lower_fence"] < 0 < st["upper_fence"]
    for key in ("mean", "std", "min", "max", "skewness", "q1", "q3", "n_unique", "unique_ratio", "top_freq_pct"):
        assert key in st


def test_categorical_stats_have_mean_length():
    st = column_stats(pd.Series(["ab", "abcd", None]), "categorical")
    assert st["mean_length"] == 3.0
    assert round(st["missing_pct"], 2) == 33.33
    assert "skewness" not in st


def test_stats_on_all_missing_column_are_json_safe():
    st = column_stats(pd.Series([np.nan] * 10), "numeric")
    assert st["missing_pct"] == 100
    assert st["mean"] is None and st["skewness"] is None
    json.dumps(st, allow_nan=False)


def test_round_stat():
    assert round_stat(np.nan) is None and round_stat(np.inf) is None
    assert round_stat(3.14159265) == 3.142
    assert round_stat(np.int64(7)) == 7


def test_histogram_bounded_on_large_column():
    cd = chart_data(pd.Series(np.random.default_rng(0).normal(size=300_000)), "numeric")
    assert cd["kind"] == "histogram"
    assert len(cd["counts"]) <= 30 and len(cd["edges"]) == len(cd["counts"]) + 1
    assert sum(cd["counts"]) == 300_000


def test_bar_chart_bounded():
    cd = chart_data(pd.Series([f"c{i}" for i in range(500)] * 2), "categorical")
    assert cd["kind"] == "bar"
    assert len(cd["labels"]) <= 20 and cd["labels"][-1] == "Other"
    assert sum(cd["counts"]) == 1000


def test_near_unique_column_gets_a_note_not_bars():
    cd = chart_data(pd.Series([f"tx{i}" for i in range(500)] + [None]), "categorical")
    assert cd == {"kind": "unique", "n_unique": 500, "unique_pct": 100.0}
    few = chart_data(pd.Series(["a", "b", "c"]), "categorical")   # all bars fit: still a chart
    assert few["kind"] == "bar"


def test_time_only_column_charts_rows_per_hour():
    rng = np.random.default_rng(0)
    secs = rng.integers(0, 86400, 3000)
    s = pd.Series([f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}" for x in secs])   # near-unique
    cd = chart_data(s, "datetime")
    assert cd["kind"] == "histogram" and cd["edges"] == list(range(25))
    assert sum(cd["counts"]) == 3000 and cd["counts"][14] == int(((secs // 3600) == 14).sum())
    assert cd["x_label"] == "Hour of day"


def test_date_column_charts_histogram_over_time():
    """Dates are binned over time (<= 30 bins, ISO edges), not drawn as top-20 values."""
    rng = np.random.default_rng(0)
    days = pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 365, 5000), unit="D")
    s = pd.Series(days.strftime("%d/%m/%Y").tolist() + [None, "not a date"])   # text, as read from a CSV
    cd = chart_data(s, "datetime")
    assert cd["kind"] == "histogram" and cd["x_type"] == "date"
    assert len(cd["counts"]) <= 30 and len(cd["edges"]) == len(cd["counts"]) + 1
    assert sum(cd["counts"]) == 5000                       # unparseable values and NaN not counted
    edges = pd.to_datetime(cd["edges"])
    assert edges[0] == pd.Timestamp("2023-01-01") and edges[-1] >= days.max()
    assert edges.is_monotonic_increasing
    json.dumps(cd, allow_nan=False)


def test_date_column_edge_cases():
    one_day = chart_data(pd.Series(["2024-05-01"] * 10), "datetime")       # a single date
    assert one_day["kind"] == "histogram" and one_day["counts"] == [10]
    assert len(one_day["edges"]) == 2 and one_day["edges"][0] < one_day["edges"][1]
    assert chart_data(pd.Series([None, "nope"]), "datetime")["counts"] == []   # nothing parses
    real = chart_data(pd.Series(pd.date_range("2020-01-01", periods=100, freq="h")), "datetime")
    assert real["x_type"] == "date" and sum(real["counts"]) == 100       # datetime64 dtype (Excel)


def test_correlation_numeric_only(mixed_df):
    cm = correlation_matrix(mixed_df, ["num", "sym"])
    assert cm["columns"] == ["num", "sym"]
    assert cm["matrix"][0][0] == 1.0
    json.dumps(cm, allow_nan=False)


def test_finding_to_dict_roundtrip():
    f = Finding("a", "skewness", {"skewness": 2.0}, "log1p", "r", [Alternative("log1p", "x")])
    d = f.to_dict()
    assert d["alternatives"][0] == {"option": "log1p", "tradeoff": "x"}
    assert d["severity"] == "info" and d["column"] == "a"
