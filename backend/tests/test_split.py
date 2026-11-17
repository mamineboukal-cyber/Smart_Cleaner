import numpy as np
import pandas as pd

from app.split import detect_task, prepare_and_split


def test_detect_task():
    assert detect_task(pd.Series([0, 1] * 50)) == "classification"
    assert detect_task(pd.Series(["a", "b", "c"] * 10)) == "classification"
    assert detect_task(pd.Series(np.linspace(0, 1, 100))) == "regression"


def test_duplicates_removed_before_split():
    df = pd.DataFrame({"x": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "y": [0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]})
    r = prepare_and_split(df, "supervised", "y")
    assert r.n_duplicates == 1 and r.n_rows_raw == 11
    assert len(r.train) + len(r.test) == 10


def test_stratified_keeps_class_ratio():
    df = pd.DataFrame({"x": range(1000), "y": [1] * 50 + [0] * 950})
    r = prepare_and_split(df, "supervised", "y")
    assert r.stratified and r.task == "classification"
    assert len(r.test) == 200
    assert abs(r.test["y"].mean() - 0.05) < 0.01


def test_missing_target_rows_dropped():
    df = pd.DataFrame({"x": range(100), "y": [0, 1] * 45 + [np.nan] * 10})
    r = prepare_and_split(df, "supervised", "y")
    assert r.n_target_missing == 10
    assert r.train["y"].notna().all() and r.test["y"].notna().all()


def test_unsupervised_random_split():
    r = prepare_and_split(pd.DataFrame({"x": range(100)}), "unsupervised", None)
    assert r.task is None and not r.stratified and len(r.test) == 20


def test_regression_not_stratified():
    df = pd.DataFrame({"x": range(100), "y": np.linspace(0, 1, 100)})
    r = prepare_and_split(df, "supervised", "y")
    assert r.task == "regression" and not r.stratified


def test_singleton_class_falls_back_with_warning():
    df = pd.DataFrame({"x": range(100), "y": [0] * 60 + [1] * 39 + [2]})
    r = prepare_and_split(df, "supervised", "y")
    assert not r.stratified and len(r.warnings) == 1


def test_split_is_reproducible():
    df = pd.DataFrame({"x": range(100)})
    a = prepare_and_split(df, "unsupervised", None)
    b = prepare_and_split(df, "unsupervised", None)
    assert a.test.index.tolist() == b.test.index.tolist()
