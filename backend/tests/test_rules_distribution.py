import numpy as np
import pandas as pd

from app.rules.distribution import check_outliers, check_skewness, outlier_target_rates
from tests.conftest import ctx_for


def with_outliers(n_normal: int, n_out: int) -> pd.Series:
    """Uniform 0-10 values (no IQR outliers) plus n_out values at 100."""
    return pd.Series(np.concatenate([np.linspace(0, 10, n_normal), [100.0] * n_out]))


def fraud_target() -> pd.Series:
    """2% fraud overall; half of the 20 outlier rows are fraud."""
    y = np.zeros(1000, dtype=int)
    y[:10] = 1          # 10 frauds among the normal rows
    y[-10:] = 1         # 10 frauds among the 20 outlier rows
    return pd.Series(y)


def test_few_outliers_capped():
    s = with_outliers(980, 20)
    f = check_outliers(s, ctx_for(s, "numeric"))
    assert f.recommendation == "cap" and f.stats["outlier_pct"] == 2.0
    assert {a.option for a in f.alternatives} == {"cap", "drop_rows", "none"}


def test_many_outliers_none():
    s = with_outliers(900, 100)
    f = check_outliers(s, ctx_for(s, "numeric"))
    assert f.recommendation == "none" and "robust" in f.reason.lower()


def test_signal_overrides_low_share():
    s = with_outliers(980, 20)
    f = check_outliers(s, ctx_for(s, "numeric", target=fraud_target(), task="classification"))
    assert f.recommendation == "none"
    assert f.stats["outlier_target_rate"] >= 2 * f.stats["overall_target_rate"]
    assert "50" in f.reason and "2" in f.reason


def test_target_rates_use_smallest_class():
    s = with_outliers(980, 20)
    rates = outlier_target_rates(s, ctx_for(s, "numeric", target=fraud_target(), task="classification"))
    assert rates == (50.0, 2.0)


def test_signal_skipped_for_regression():
    s = with_outliers(980, 20)
    y = pd.Series(np.arange(1000, dtype=float))
    ctx = ctx_for(s, "numeric", target=y, task="regression")
    assert outlier_target_rates(s, ctx) is None
    assert check_outliers(s, ctx).recommendation == "cap"


def test_no_outliers_no_finding():
    s = pd.Series(np.linspace(0, 10, 100))
    assert check_outliers(s, ctx_for(s, "numeric")) is None


def test_positive_skew_log1p():
    s = pd.Series(np.random.default_rng(0).exponential(size=1000))
    f = check_skewness(s, ctx_for(s, "numeric"))
    assert f.recommendation == "log1p"
    assert {a.option for a in f.alternatives} == {"log1p", "yeo_johnson", "sqrt", "none"}


def test_negative_values_yeo_johnson():
    s = pd.Series(np.random.default_rng(0).exponential(size=1000) - 5)
    f = check_skewness(s, ctx_for(s, "numeric"))
    assert f.recommendation == "yeo_johnson"
    assert {a.option for a in f.alternatives} == {"yeo_johnson", "none"}


def test_symmetric_no_skew_finding():
    s = pd.Series(np.random.default_rng(0).normal(size=1000))
    assert check_skewness(s, ctx_for(s, "numeric")) is None


def test_target_rates_use_exact_not_rounded_fences():
    # values at 16.67 sit above the exact fence 16.6685 but not above the rounded 16.67
    s = pd.Series(np.concatenate([np.linspace(0, 10, 900), [16.67] * 100]))
    y = pd.Series([0] * 900 + [1] * 100)
    rates = outlier_target_rates(s, ctx_for(s, "numeric", target=y, task="classification"))
    assert rates == (100.0, 10.0)
