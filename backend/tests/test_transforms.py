import numpy as np
import pandas as pd
from sklearn.preprocessing import PowerTransformer

from app.profiling import iqr_fences
from app.transforms import ColumnPipeline

TRAIN = pd.DataFrame({"x": [1, 2, 3, np.nan]})
TEST = pd.DataFrame({"x": [100, 200, np.nan]})


def test_median_from_train_only():
    p = ColumnPipeline("x", "numeric", {"missing": "median"}).fit(TRAIN)
    assert p.transform(TEST, is_train=False)["x"].iloc[2] == 2.0


def test_mean_and_constant_fill():
    assert ColumnPipeline("x", "numeric", {"missing": "mean"}).fit(TRAIN).transform(TEST, False)["x"].iloc[2] == 2.0
    assert ColumnPipeline("x", "numeric", {"missing": "constant"}).fit(TRAIN).transform(TEST, False)["x"].iloc[2] == 0.0


def test_categorical_mode_and_missing_label():
    train = pd.DataFrame({"c": ["a", "a", "b", None]})
    test = pd.DataFrame({"c": [None, "b"]})
    mode = ColumnPipeline("c", "categorical", {"missing": "mode"}).fit(train).transform(test, False)
    assert list(mode["c"]) == ["a", "b"]
    miss = ColumnPipeline("c", "categorical", {"missing": "constant_missing"}).fit(train).transform(test, False)
    assert list(miss["c"]) == ["Missing", "b"]


def test_drop_rows_train_only():
    p = ColumnPipeline("x", "numeric", {"missing": "drop_rows"}).fit(TRAIN)
    assert list(p.train_rows_to_drop(TRAIN)) == [3]
    assert p.transform(TEST, is_train=False)["x"].isna().sum() == 0   # test imputed with train median
    assert p.transform(TEST, is_train=False)["x"].iloc[2] == 2.0


def test_cap_uses_train_fences():
    train = pd.DataFrame({"x": np.linspace(0, 10, 100)})
    _, _, lo, hi = iqr_fences(train["x"])
    p = ColumnPipeline("x", "numeric", {"outliers": "cap"}).fit(train)
    out = p.transform(pd.DataFrame({"x": [1e6, -1e6, 5.0]}), False)["x"]
    assert list(out) == [hi, lo, 5.0]


def test_outlier_drop_rows_train_only_and_test_capped():
    train = pd.DataFrame({"x": list(np.linspace(0, 10, 99)) + [1000.0]})
    p = ColumnPipeline("x", "numeric", {"outliers": "drop_rows"}).fit(train)
    assert list(p.train_rows_to_drop(train)) == [99]
    _, _, _, hi = iqr_fences(train["x"])
    assert p.transform(pd.DataFrame({"x": [1e6]}), False)["x"].iloc[0] == hi


def test_log1p_on_test_negative_is_finite():
    train = pd.DataFrame({"x": [0, 1, 2, 3, 100.0]})
    test = pd.DataFrame({"x": [-5.0, 1.0]})
    out = ColumnPipeline("x", "numeric", {"skewness": "log1p"}).fit(train).transform(test, False)
    assert np.isfinite(out["x"]).all() and out["x"].iloc[1] == np.log1p(1.0)


def test_sqrt_clips_to_train_min():
    train = pd.DataFrame({"x": [4.0, 9.0, 16.0]})
    out = ColumnPipeline("x", "numeric", {"skewness": "sqrt"}).fit(train).transform(pd.DataFrame({"x": [-1.0, 9.0]}), False)
    assert list(out["x"]) == [2.0, 3.0]


def test_yeo_johnson_fitted_on_train():
    rng = np.random.default_rng(0)
    train = pd.DataFrame({"x": list(rng.exponential(size=50) - 1) + [np.nan]})
    test = pd.DataFrame({"x": [100.0, np.nan]})
    p = ColumnPipeline("x", "numeric", {"skewness": "yeo_johnson"}).fit(train)
    ref = PowerTransformer(method="yeo-johnson", standardize=False).fit(train["x"].dropna().to_numpy().reshape(-1, 1))
    assert np.isclose(p.params["skewness"]["lambda"], ref.lambdas_[0])
    out = p.transform(test, False)["x"]
    assert np.isclose(out.iloc[0], ref.transform([[100.0]])[0, 0]) and np.isnan(out.iloc[1])


def test_drop_column_returns_empty():
    p = ColumnPipeline("x", "numeric", {"missing": "median", "id_like": "drop_column"}).fit(TRAIN)
    assert p.dropped and p.transform(TEST, False).shape == (3, 0)
    assert p.applied() == {"id_like": "drop_column"}


def test_datetime_extract():
    train = pd.DataFrame({"d": ["2020-01-15", "2021-06-30", None]})
    test = pd.DataFrame({"d": ["2022-03-01", None]}, index=[10, 11])
    out = ColumnPipeline("d", "datetime", {"datetime": "extract"}).fit(train).transform(test, False)
    assert list(out.columns) == ["d_year", "d_month", "d_day", "d_dayofweek"]
    assert list(out.index) == [10, 11]
    assert out.loc[10].tolist() == [2022, 3, 1, 1]   # 2022-03-01 is a Tuesday
    assert out.loc[11, "d_year"] == 2020             # NaT -> train median of the part (int)
    assert all(pd.api.types.is_integer_dtype(out[c]) for c in out)


def test_applied_reports_choices():
    p = ColumnPipeline("x", "numeric", {"missing": "median", "outliers": "none", "skewness": "log1p"}).fit(TRAIN)
    assert p.applied() == {"missing": "median", "skewness": "log1p"}


def test_index_preserved():
    test = pd.DataFrame({"x": [5.0, np.nan]}, index=["r1", "r2"])
    out = ColumnPipeline("x", "numeric", {"missing": "median"}).fit(TRAIN).transform(test, False)
    assert list(out.index) == ["r1", "r2"]
