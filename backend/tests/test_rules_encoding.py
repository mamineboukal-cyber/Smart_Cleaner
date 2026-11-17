import numpy as np
import pandas as pd

from app.profiling import iqr_fences
from app.rules.encoding import check_encoding, check_scaling
from tests.conftest import ctx_for

ENCODING_OPTIONS = {"onehot", "ordinal", "frequency", "drop_column"}
SCALING_OPTIONS = {"standard", "minmax", "robust", "none"}


def heavy_tail_series() -> pd.Series:
    """10% of values far above the Tukey fence."""
    return pd.Series(np.concatenate([np.linspace(0, 10, 900), [100.0] * 100]))


def test_low_cardinality_onehot():
    s = pd.Series(["a", "b", "c"] * 10)
    f = check_encoding(s, ctx_for(s, "categorical"))
    assert f.recommendation == "onehot" and f.stats["n_unique"] == 3
    assert {a.option for a in f.alternatives} == ENCODING_OPTIONS


def test_ten_categories_still_onehot():
    s = pd.Series([f"c{i}" for i in range(10)] * 5)
    assert check_encoding(s, ctx_for(s, "categorical")).recommendation == "onehot"


def test_high_cardinality_frequency():
    s = pd.Series([f"c{i}" for i in range(11)] * 5)
    f = check_encoding(s, ctx_for(s, "categorical"))
    assert f.recommendation == "frequency" and "10" in f.reason
    assert {a.option for a in f.alternatives} == ENCODING_OPTIONS


def test_numeric_not_encoded():
    s = pd.Series(np.linspace(0, 1, 50))
    assert check_encoding(s, ctx_for(s, "numeric")) is None


def test_scaling_robust_when_many_outliers():
    s = heavy_tail_series()
    f = check_scaling(s, ctx_for(s, "numeric"))
    assert f.recommendation == "robust" and f.stats["outlier_pct"] == 10.0
    assert {a.option for a in f.alternatives} == SCALING_OPTIONS


def test_scaling_standard_otherwise():
    s = pd.Series(np.linspace(0, 10, 100))
    assert check_scaling(s, ctx_for(s, "numeric")).recommendation == "standard"


def test_scaling_not_for_categorical():
    s = pd.Series(["a", "b"] * 5)
    assert check_scaling(s, ctx_for(s, "categorical")) is None


def test_scaling_recomputed_after_capping_changes_recommendation():
    s = heavy_tail_series()
    assert check_scaling(s, ctx_for(s, "numeric")).recommendation == "robust"
    _, _, lo, hi = iqr_fences(s)  # exact fences, as the cap transformer uses (stats are rounded)
    capped = s.clip(lo, hi)
    assert check_scaling(capped, ctx_for(capped, "numeric")).recommendation == "standard"
