import numpy as np
import pandas as pd

from app.types import apply_type_overrides, infer_types


def test_infer_types():
    df = pd.DataFrame({
        "amount": np.arange(100) * 1.5,
        "pclass": [1, 2, 3, 1] * 25,
        "city": ["a", "b"] * 50,
        "when": pd.date_range("2020-01-01", periods=100).astype(str),
        "flag": [True, False] * 50,
    })
    assert infer_types(df) == {
        "amount": "numeric",
        "pclass": "categorical",
        "city": "categorical",
        "when": "datetime",
        "flag": "categorical",
    }


def test_datetime64_dtype_is_datetime():
    df = pd.DataFrame({"d": pd.date_range("2020-01-01", periods=5)})
    assert infer_types(df)["d"] == "datetime"


def test_mostly_unparseable_dates_stay_categorical():
    s = ["2020-01-01"] * 6 + ["garbage"] * 4
    assert infer_types(pd.DataFrame({"d": s}))["d"] == "categorical"


def test_overrides_replace_types():
    assert apply_type_overrides({"a": "numeric", "b": "numeric"}, {"a": "categorical"}) == {
        "a": "categorical",
        "b": "numeric",
    }


def test_time_only_detection():
    import datetime as dt

    from app.types import is_time_only

    assert is_time_only(pd.Series(["14:32:05", "09:15", "23:59:59", None]))
    assert is_time_only(pd.Series([dt.time(14, 3), dt.time(9, 5)]))   # Excel time cells
    assert not is_time_only(pd.Series(["2020-01-01 14:32", "2020-01-02 09:15"]))
    assert not is_time_only(pd.Series(pd.date_range("2020-01-01", periods=3, freq="h")))
    assert not is_time_only(pd.Series(["a", "b"]))
