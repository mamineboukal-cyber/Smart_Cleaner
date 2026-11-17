"""Column type inference: numeric, categorical or datetime."""

import warnings

import pandas as pd

MAX_CATEGORICAL_INT_UNIQUE = 10   # integers with <= 10 distinct values are categories (e.g. Pclass)
DATETIME_PARSE_MIN = 0.90         # >= 90% of values must parse as dates
DATETIME_SAMPLE = 1000            # only the first 1000 non-null values are checked, for speed


def date_parse_rate(s: pd.Series) -> float:
    """Share of non-null values (first 1000) that parse as dates."""
    values = s.dropna().astype(str).head(DATETIME_SAMPLE)
    if values.empty:
        return 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    return float(parsed.notna().mean())


def _is_texty(s: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def infer_column_type(s: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if pd.api.types.is_bool_dtype(s):
        return "categorical"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric" if s.nunique(dropna=True) > MAX_CATEGORICAL_INT_UNIQUE else "categorical"
    if _is_texty(s) and date_parse_rate(s) >= DATETIME_PARSE_MIN:
        return "datetime"
    return "categorical"


def infer_types(df: pd.DataFrame) -> dict[str, str]:
    """Map each column name to "numeric", "categorical" or "datetime"."""
    return {str(c): infer_column_type(df[c]) for c in df.columns}


def apply_type_overrides(types: dict[str, str], overrides: dict[str, str]) -> dict[str, str]:
    """User-chosen types win over inferred ones."""
    return {**types, **{k: v for k, v in overrides.items() if k in types}}
