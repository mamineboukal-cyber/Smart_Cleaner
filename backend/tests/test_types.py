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
