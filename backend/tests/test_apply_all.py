import numpy as np
import pandas as pd

from app.split import prepare_and_split
from app.transforms import apply_all
from app.types import infer_types


def test_apply_all_no_leakage(mixed_df):
    split = prepare_and_split(mixed_df, "supervised", "target")
    choices = {"num": {"missing": "median", "scaling": "standard"}}
    r = apply_all(split, infer_types(mixed_df), choices, "target")
    num_train_after_impute = split.train["num"].fillna(split.train["num"].median())
    assert abs(r.train["num"].mean()) < 1e-9                       # standardised on train
    expected = (split.test["num"].fillna(split.train["num"].median()) - num_train_after_impute.mean()) \
        / num_train_after_impute.std(ddof=0)
    pd.testing.assert_series_equal(r.test["num"], expected, check_names=False)
    assert r.applied["num"] == {"missing": "median", "scaling": "standard"}


def test_apply_all_target_untouched_and_rows_dropped_train_only(mixed_df):
    split = prepare_and_split(mixed_df, "supervised", "target")
    n_nan = int(split.train["num"].isna().sum())
    choices = {"num": {"missing": "drop_rows"}, "const_col": {"constant": "drop_column"},
               "cat": {"encoding": "onehot"}}
    r = apply_all(split, infer_types(mixed_df), choices, "target")
    assert n_nan > 0 and r.rows_dropped_train == n_nan
    assert len(r.train) == len(split.train) - n_nan and len(r.test) == len(split.test)
    assert r.test["num"].isna().sum() == 0
    pd.testing.assert_series_equal(r.test["target"], split.test["target"])
    assert list(r.train.columns)[-1] == "target"
    assert "const_col" not in r.train and "cat" not in r.train and "cat_red" in r.train
    assert "const_col" not in r.applied or r.applied["const_col"] == {"constant": "drop_column"}


def test_apply_all_records_scaling_finding_after_cap():
    df = pd.DataFrame({"x": np.concatenate([np.linspace(0, 10, 900), np.linspace(100, 200, 100)])})  # distinct: not deduplicated
    split = prepare_and_split(df, "unsupervised", None)
    r = apply_all(split, {"x": "numeric"}, {"x": {"outliers": "cap"}}, None)
    assert r.scaling_findings["x"].recommendation == "standard"
    r2 = apply_all(split, {"x": "numeric"}, {}, None)
    assert r2.scaling_findings["x"].recommendation == "robust"
