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


def test_letter_prefixed_ids_are_not_dates():
    # dateutil reads "T15" as day 15 and "T2399" as year 2399; an ID is not a date.
    from app.types import infer_column_type

    assert infer_column_type(pd.Series([f"T{i}" for i in range(3000)])) == "categorical"


def _dates(values, **kw):
    from app.types import to_datetime
    return to_datetime(pd.Series(values), **kw)


def test_day_first_detected_from_unambiguous_value():
    from app.types import detect_dayfirst
    s = pd.Series(["27/09/2025", "05/01/2025", None])
    assert detect_dayfirst(s) is True
    d = _dates(s)
    assert (d[0].month, d[0].day) == (9, 27) and (d[1].month, d[1].day) == (1, 5)   # 5 January


def test_month_first_detected_from_unambiguous_value():
    from app.types import detect_dayfirst
    s = pd.Series(["09/27/2025", "05/01/2025"])
    assert detect_dayfirst(s) is False
    d = _dates(s)
    assert (d[0].month, d[0].day) == (9, 27) and (d[1].month, d[1].day) == (5, 1)    # 1 May


def test_all_ambiguous_defaults_to_day_first():
    d = _dates(["05/01/2025", "03/02/2025 14:30", "07.08.2025", "01-02-2025"])
    assert [(x.month, x.day) for x in d] == [(1, 5), (2, 3), (8, 7), (2, 1)]
    assert d[1].hour == 14 and d[1].minute == 30


def test_iso_and_real_datetimes_unaffected():
    from app.types import detect_dayfirst
    d = _dates(["2025-01-05", "2025-01-05 08:00:00", "2025-12-31"])
    assert [(x.month, x.day) for x in d] == [(1, 5), (1, 5), (12, 31)]
    assert detect_dayfirst(pd.Series(["2025-01-05"])) is False
    real = pd.Series(pd.to_datetime(["2025-01-05"]))
    assert _dates(real)[0].month == 1


def test_explicit_dayfirst_overrides_detection():
    d = _dates(["01/13/2025", "05/01/2025"], dayfirst=True)   # e.g. decided on train
    assert (d[1].month, d[1].day) == (1, 5)
