"""Before/after preview of one column's chosen transformations, on train only."""

import pandas as pd

from app.profiling import chart_data, column_stats
from app.rules.context import ColumnContext
from app.rules.encoding import check_scaling
from app.transforms import ColumnPipeline

MAX_AFTER_COLUMNS = 20   # one-hot can produce many columns; the preview shows the first 20


def _summary(s: pd.Series, col_type: str) -> dict:
    return {"stats": column_stats(s, col_type), "chart": chart_data(s, col_type)}


def preview_column(train: pd.DataFrame, column: str, col_type: str, column_choices: dict[str, str]) -> dict:
    pipeline = ColumnPipeline(column, col_type, column_choices).fit(train)
    dropped_rows = pipeline.train_rows_to_drop(train)
    kept = train.drop(index=dropped_rows)
    out = pipeline.transform(kept, is_train=True)

    after = []
    for name in list(out.columns)[:MAX_AFTER_COLUMNS]:
        s = out[name]
        out_type = "numeric" if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) else "categorical"
        after.append({"name": str(name), **_summary(s, out_type)})

    scaling = None
    if col_type == "numeric":
        pre = pipeline.pre_scaling(kept)
        if pre is not None:
            ctx = ColumnContext("numeric", column_stats(pre, "numeric"))
            scaling = check_scaling(pre, ctx).to_dict()

    return {
        "before": _summary(train[column], col_type),
        "after": after,
        "scaling": scaling,
        "rows_dropped": int(len(dropped_rows)),
    }
