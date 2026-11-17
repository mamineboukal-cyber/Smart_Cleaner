from dataclasses import dataclass

import pandas as pd

from app.findings import Alternative
from app.i18n import t


@dataclass
class ColumnContext:
    """Everything a rule needs besides the column itself.

    ``stats`` come from ``column_stats`` on the train split; ``target`` is the
    train target aligned to the series (None when unsupervised).
    """

    col_type: str
    stats: dict
    target: pd.Series | None = None
    task: str | None = None  # "classification" | "regression" | None


def alternatives(*options: str) -> list[Alternative]:
    """Every option with its trade-off sentence (the recommendation is listed too)."""
    return [Alternative(o, t(f"tradeoff.{o}")) for o in options]
