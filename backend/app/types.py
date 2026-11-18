"""Column type inference: numeric, categorical or datetime."""

import re
import warnings

import pandas as pd

MAX_CATEGORICAL_INT_UNIQUE = 10   # integers with <= 10 distinct values are categories (e.g. Pclass)
DATETIME_PARSE_MIN = 0.90         # >= 90% of values must parse as dates
DATETIME_SAMPLE = 1000            # only the first 1000 non-null values are checked, for speed
# A date or time has at least two digit groups ("2020-01-15", "15/01/2020", "Jan 15, 2020",
# "14:32"). dateutil also accepts a single number ("T15" -> day 15, "T2399" -> year 2399),
# which would turn ID columns into dates, so values without this shape never count.
DATE_SHAPE = re.compile(r"\d+\D+\d+")
# "14:32", "14:32:05", "14:32:05.120", "2:32 PM": a time of day with no date
TIME_ONLY = re.compile(r"^\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?(\s*[AaPp]\.?[Mm]\.?)?$")


def to_datetime(s: pd.Series) -> pd.Series:
    """Parse to datetime64 (unparseable -> NaT). Values go through str first, so
    Excel time cells (``datetime.time``) parse too; a time of day gets today's
    date, which callers that only read the hour/minute ignore."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(s.astype(str).where(s.notna()), errors="coerce", format="mixed")


def is_time_only(s: pd.Series) -> bool:
    """True when >= 90% of non-null values (first 1000) are a time of day without a date."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return False   # a real timestamp always carries a date
    values = s.dropna().astype(str).str.strip().head(DATETIME_SAMPLE)
    if values.empty:
        return False
    return float(values.str.match(TIME_ONLY).mean()) >= DATETIME_PARSE_MIN


def date_parse_rate(s: pd.Series) -> float:
    """Share of non-null values (first 1000) that look like dates and parse as dates."""
    values = s.dropna().astype(str).head(DATETIME_SAMPLE)
    if values.empty:
        return 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    return float((parsed.notna() & values.str.contains(DATE_SHAPE)).mean())


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
