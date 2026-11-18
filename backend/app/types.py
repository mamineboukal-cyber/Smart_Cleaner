"""Column type inference: numeric, categorical or datetime."""

import datetime
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


# "27/09/2025", "05.01.2025 14:30", "1-2-25": two 1-2 digit groups before the year.
# ISO dates ("2025-01-05") start with the year and never match, so they are unaffected.
NUMERIC_DATE = re.compile(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-]\d{2,4}\b")


def detect_dayfirst(s: pd.Series) -> bool:
    """Whether "dd/mm/yyyy"-style values put the day first.

    An unambiguous value decides: 27/09 can only be day-first, 09/27 only
    month-first (the majority wins if a column has both). When every value is
    ambiguous (05/01), day-first is assumed: the data and users are European.
    Returns False when no value has this shape (ISO dates, real datetimes)."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return False
    parts = s.dropna().astype(str).head(DATETIME_SAMPLE).str.extract(NUMERIC_DATE).dropna()
    if parts.empty:
        return False
    first, second = parts[0].astype(int), parts[1].astype(int)
    return bool((first > 12).sum() >= (second > 12).sum())


def _excel_swapped_cells(s: pd.Series) -> pd.Series | None:
    """Mask of date cells that Excel created by misreading day-first text, or None.

    Excel in a month-first locale converts "01/07/2025" (1 July) into the date
    7 January, but leaves "13/07/2025" as text (there is no month 13). The
    signature, all required: text cells are dd/mm/yyyy with a day > 12; real
    date cells exist, all at midnight with a day <= 12 (genuine dates over a
    period would include days 13-31)."""
    if not pd.api.types.is_object_dtype(s):
        return None
    values = s.dropna()
    is_date = values.map(lambda v: isinstance(v, datetime.datetime))
    text = values[~is_date].astype(str)
    parts = text.str.extract(NUMERIC_DATE).dropna()
    if not is_date.any() or parts.empty or len(parts) < len(text) * DATETIME_PARSE_MIN:
        return None
    if not (parts[0].astype(int) > 12).all():
        return None   # Excel could have converted these but didn't: not its doing
    dates = pd.to_datetime(values[is_date])
    if not ((dates.dt.day <= 12) & (dates == dates.dt.normalize())).all():
        return None
    return is_date.reindex(s.index, fill_value=False)


def repair_excel_swapped_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Swap day and month back in date cells Excel misread (see ``_excel_swapped_cells``).
    Returns a repaired copy and {column: number of cells repaired}."""
    out, repairs = df.copy(), {}
    for col in df.columns:
        mask = _excel_swapped_cells(df[col])
        if mask is None:
            continue
        out[col] = df[col].astype(object)
        out.loc[mask, col] = df.loc[mask, col].map(lambda v: v.replace(month=v.day, day=v.month))
        repairs[str(col)] = int(mask.sum())
    return out, repairs


def to_datetime(s: pd.Series, dayfirst: bool | None = None) -> pd.Series:
    """Parse to datetime64 (unparseable -> NaT). Values go through str first, so
    Excel time cells (``datetime.time``) parse too; a time of day gets today's
    date, which callers that only read the hour/minute ignore.

    ``dayfirst`` is detected from ``s`` when not given; pass the value decided on
    train so the test split is read the same way."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    if dayfirst is None:
        dayfirst = detect_dayfirst(s)
    text = s.astype(str).where(s.notna())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(text, errors="coerce", format="mixed")
        if dayfirst:
            # Only dd/mm/yyyy-shaped values: with dayfirst, pandas would also read "2025-01-07" as 1 July.
            ddmm = text.str.contains(NUMERIC_DATE, na=False)
            if ddmm.any():
                parsed[ddmm] = pd.to_datetime(text[ddmm], errors="coerce", format="mixed", dayfirst=True)
    return parsed


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
        parsed = to_datetime(values)
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
