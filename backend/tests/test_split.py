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


def _split_fingerprint_in_new_process(hash_seed: str) -> str:
    """Run the split in a fresh interpreter (like a server restart) and return the train/test row order."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    code = (
        "import numpy as np, pandas as pd\n"
        "from app.split import prepare_and_split\n"
        "rng = np.random.default_rng(3)\n"
        "df = pd.DataFrame({'amount': rng.exponential(100, 500), 'cat': rng.choice(list('abc'), 500),"
        " 'y': rng.choice(['no', 'yes'], 500, p=[0.9, 0.1])})\n"
        "r = prepare_and_split(df, 'supervised', 'y')\n"
        "print(list(r.train.index), list(r.test.index))\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    backend = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env,
                         capture_output=True, text=True, check=True)
    return out.stdout


def test_split_is_identical_across_runs_and_restarts():
    """The same data and settings always give the same train/test rows: the split is seeded
    (random_state=42) and nothing before it depends on hashing or wall-clock time."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"amount": rng.exponential(100, 500), "cat": rng.choice(list("abc"), 500),
                       "y": rng.choice(["no", "yes"], 500, p=[0.9, 0.1])})
    for mode, target in (("supervised", "y"), ("unsupervised", None)):
        a, b = prepare_and_split(df, mode, target), prepare_and_split(df.copy(), mode, target)
        pd.testing.assert_frame_equal(a.train, b.train)
        pd.testing.assert_frame_equal(a.test, b.test)
    assert _split_fingerprint_in_new_process("0") == _split_fingerprint_in_new_process("12345")


def test_split_depends_on_row_order_and_settings():
    """Documents what *does* change the split, so a different number is explainable:
    the mode/target (stratified vs random) and the order of the rows in the file."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"amount": rng.exponential(100, 500), "y": rng.choice([0, 1], 500, p=[0.9, 0.1])})
    base = set(prepare_and_split(df, "supervised", "y").train["amount"])
    assert set(prepare_and_split(df, "unsupervised", None).train["amount"]) != base
    shuffled = df.sample(frac=1, random_state=0).reset_index(drop=True)
    assert set(prepare_and_split(shuffled, "supervised", "y").train["amount"]) != base
