import json

import numpy as np
import pandas as pd

from app.preview import preview_column

RNG = np.random.default_rng(0)
TRAIN = pd.DataFrame({
    "amount": RNG.exponential(scale=100, size=500),
    "heavy": np.concatenate([np.linspace(0, 10, 450), np.linspace(100, 200, 50)]),
    "gappy": [np.nan] * 50 + list(RNG.normal(size=450)),
    "cat": RNG.choice(list("abcdefghijklmnopqrstuvwxyz"), size=500),
})


def test_preview_log_reduces_skew():
    r = preview_column(TRAIN, "amount", "numeric", {"skewness": "log1p"})
    assert abs(r["after"][0]["stats"]["skewness"]) < abs(r["before"]["stats"]["skewness"])
    assert r["after"][0]["name"] == "amount" and r["after"][0]["chart"]["kind"] == "histogram"
    json.dumps(r, allow_nan=False)


def test_preview_returns_updated_scaling_after_cap():
    assert preview_column(TRAIN, "heavy", "numeric", {})["scaling"]["recommendation"] == "robust"
    r = preview_column(TRAIN, "heavy", "numeric", {"outliers": "cap"})
    assert r["scaling"]["recommendation"] == "standard"


def test_preview_drop_rows_count():
    r = preview_column(TRAIN, "gappy", "numeric", {"missing": "drop_rows"})
    assert r["rows_dropped"] == 50 and r["after"][0]["stats"]["count"] == 450


def test_preview_dropped_column_has_empty_after():
    r = preview_column(TRAIN, "amount", "numeric", {"id_like": "drop_column"})
    assert r["after"] == [] and r["scaling"] is None and r["before"]["stats"]["count"] == 500


def test_preview_onehot_capped_at_20_columns():
    r = preview_column(TRAIN, "cat", "categorical", {"encoding": "onehot"})
    assert len(r["after"]) == 20 and r["scaling"] is None
    assert r["before"]["chart"]["kind"] == "bar"
