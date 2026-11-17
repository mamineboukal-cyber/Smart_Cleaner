"""The shared result type of every rule.

A ``Finding`` carries the numbers (``stats``), the recommendation, a reason
that quotes those numbers, and every alternative with its trade-off. The EDA
tab, the Preprocessing tab and the Excel report all read the same objects,
so they can never disagree.
"""

import math
from dataclasses import asdict, dataclass, field

import numpy as np

# --- Rule names ---
DUPLICATES = "duplicates"
CONSTANT = "constant"
ID_LIKE = "id_like"
FREE_TEXT = "free_text"
DATETIME = "datetime"
MISSING = "missing"
OUTLIERS = "outliers"
SKEWNESS = "skewness"
ENCODING = "encoding"
SCALING = "scaling"
CORRELATION = "correlation"
IMBALANCE = "imbalance"
ANALYSIS_FAILED = "analysis_failed"

# --- Options ---
NONE = "none"
KEEP = "keep"
DROP_COLUMN = "drop_column"
DROP_ROWS = "drop_rows"
MEAN = "mean"
MEDIAN = "median"
MODE = "mode"
CONSTANT_FILL = "constant"
CONSTANT_MISSING = "constant_missing"
CAP = "cap"
LOG1P = "log1p"
YEO_JOHNSON = "yeo_johnson"
SQRT = "sqrt"
ONEHOT = "onehot"
ORDINAL = "ordinal"
FREQUENCY = "frequency"
STANDARD = "standard"
MINMAX = "minmax"
ROBUST = "robust"
EXTRACT = "extract"
REMOVE = "remove"
CLASS_WEIGHT_BALANCED = "class_weight_balanced"


@dataclass
class Alternative:
    option: str
    tradeoff: str


@dataclass
class Finding:
    column: str | None  # None for dataset-level findings (duplicates)
    rule: str
    stats: dict
    recommendation: str
    reason: str
    alternatives: list[Alternative]  # always includes the recommended option
    severity: str = "info"  # info | warning | error

    def to_dict(self) -> dict:
        return asdict(self)


def round_stat(x) -> float | int | None:
    """Round to 4 significant figures; NaN/inf/None become None (valid JSON)."""
    if x is None:
        return None
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    x = float(x)
    if not math.isfinite(x):
        return None
    if x == 0:
        return 0.0
    digits = 4 - int(math.floor(math.log10(abs(x)))) - 1
    return round(x, digits)
