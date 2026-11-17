"""Dataset preparation and the train/test split.

Order matters for leakage prevention:
1. exact duplicate rows are removed first (otherwise one copy could land in
   train and the other in test);
2. rows without a target are dropped (supervised only);
3. the data is split 80/20 *before* any statistic is computed, so every
   later fit sees train only.
"""

from dataclasses import dataclass, field

import pandas as pd
from sklearn.model_selection import train_test_split

from app.i18n import t

TEST_SIZE = 0.2
RANDOM_STATE = 42
MAX_CLASSIFICATION_UNIQUE = 20   # numeric targets with <= 20 distinct values are classes


@dataclass
class SplitResult:
    train: pd.DataFrame
    test: pd.DataFrame
    task: str | None            # "classification" | "regression" | None (unsupervised)
    stratified: bool
    n_rows_raw: int
    n_duplicates: int
    n_target_missing: int
    warnings: list[str] = field(default_factory=list)


def detect_task(y: pd.Series) -> str:
    if not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y):
        return "classification"
    return "classification" if y.nunique(dropna=True) <= MAX_CLASSIFICATION_UNIQUE else "regression"


def prepare_and_split(df: pd.DataFrame, mode: str, target: str | None, seed: int = RANDOM_STATE) -> SplitResult:
    n_raw = len(df)
    deduped = df.drop_duplicates()
    n_duplicates = n_raw - len(deduped)

    n_target_missing = 0
    task = None
    stratify = None
    warnings: list[str] = []
    if mode == "supervised":
        before = len(deduped)
        deduped = deduped[deduped[target].notna()]
        n_target_missing = before - len(deduped)
        task = detect_task(deduped[target])
        if task == "classification":
            counts = deduped[target].value_counts()
            if counts.min() < 2:
                warnings.append(t("warning.stratify_fallback", cls=counts.idxmin(), count=int(counts.min())))
            else:
                stratify = deduped[target]

    train, test = train_test_split(deduped, test_size=TEST_SIZE, random_state=seed, stratify=stratify)
    return SplitResult(
        train=train,
        test=test,
        task=task,
        stratified=stratify is not None,
        n_rows_raw=n_raw,
        n_duplicates=n_duplicates,
        n_target_missing=n_target_missing,
        warnings=warnings,
    )
