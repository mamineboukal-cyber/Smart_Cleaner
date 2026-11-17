import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """Small dataset that triggers most rules: skewed numeric with missing values,
    categorical, constant, ID and a binary (imbalanced) target."""
    rng = np.random.default_rng(0)
    n = 200
    num = rng.exponential(scale=10, size=n)
    num[:20] = np.nan
    return pd.DataFrame({
        "id_col": np.arange(n),
        "num": num,
        "sym": rng.normal(50, 5, size=n),
        "cat": rng.choice(["red", "green", "blue"], size=n),
        "const_col": ["same"] * n,
        "target": [1] * 20 + [0] * (n - 20),
    })


@pytest.fixture
def numeric_series_with_outliers() -> pd.Series:
    rng = np.random.default_rng(1)
    return pd.Series(np.concatenate([rng.normal(0, 1, 980), [15, 20, -18, 25] * 5]))


def ctx_for(s: pd.Series, col_type: str, target: pd.Series | None = None, task: str | None = None):
    """Build the ColumnContext a rule receives, from column_stats on ``s``."""
    from app.profiling import column_stats
    from app.rules.context import ColumnContext

    return ColumnContext(col_type=col_type, stats=column_stats(s, col_type), target=target, task=task)
