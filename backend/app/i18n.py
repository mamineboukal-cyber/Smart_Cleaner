"""All user-facing text for Smart Cleaner (English).

Every label, recommendation reason, trade-off line, warning and report header
lives in ``MESSAGES``. Code never hardcodes user-facing strings: it calls
``t(key, **values)``. Keys starting with ``ui.`` are served to the frontend
through ``GET /labels``.
"""

MESSAGES: dict[str, str] = {
    # --- UI: tabs ---
    "ui.tab.import": "Import",
    "ui.tab.eda": "Exploratory analysis",
    "ui.tab.preprocessing": "Preprocessing & cleaning",
    "ui.tab.export": "Execute & export",
    "ui.other": "Other",
    # --- Reasons (rule.recommendation) ---
    "reason.constant.drop_column": (
        "{n_unique} distinct value(s); the most frequent covers {top_freq_pct}% of rows "
        "(threshold: {threshold}%). The column carries almost no information."
    ),
    "reason.id_like.drop_column": (
        "{ratio_pct}% of values are unique (threshold: {threshold}%). The column identifies rows "
        "rather than describing them, so a model would memorise it."
    ),
    "reason.free_text.drop_column": (
        "{n_unique} distinct values (threshold: > {min_unique}) with a mean length of {mean_length} "
        "characters (threshold: > {min_length}). This looks like free text, which needs NLP rather "
        "than cleaning; it is not processed."
    ),
    "reason.datetime.extract": (
        "The column holds dates. A raw timestamp is not usable by most models, but its calendar "
        "parts (year, month, day, day of week) are."
    ),
    "reason.datetime.drop_column": (
        "{parse_pct}% of values parse as dates (between {low}% and {high}%): possible date with an "
        "inconsistent format. No extraction is attempted."
    ),
    "reason.missing.drop_column": (
        "{missing_pct}% of values are missing (threshold: > {threshold}%). With more than half "
        "the values missing, any imputed value would be mostly invented."
    ),
    "reason.missing.median": (
        "{missing_pct}% of values are missing and |skewness| = {abs_skew} > {threshold}. The mean "
        "is pulled by the long tail, so the median is the more typical value."
    ),
    "reason.missing.mean": (
        "{missing_pct}% of values are missing and |skewness| = {abs_skew} <= {threshold}. The "
        "distribution is roughly symmetric, so the mean is a fair fill-in."
    ),
    "reason.missing.mode": (
        "{missing_pct}% of values are missing. The most frequent category is the least surprising "
        "fill-in; use the constant \"Missing\" if missingness itself may carry meaning."
    ),
    "reason.outliers.signal": (
        "Among outlier rows the rarest class makes up {outlier_rate}% versus {overall_rate}% overall "
        "(at least {ratio}x). The outliers carry signal, not noise, so they are kept."
    ),
    "reason.outliers.cap": (
        "{outlier_pct}% of values fall outside the Tukey fences [{lower}, {upper}] (Q1 - 1.5*IQR, "
        "Q3 + 1.5*IQR), at most {threshold}%. Capping them at the fences limits their pull."
    ),
    "reason.outliers.heavy_tail": (
        "{outlier_pct}% of values fall outside the Tukey fences (above {threshold}%). At that share "
        "the \"outliers\" are part of the real distribution (heavy tail); robust scaling handles them."
    ),
    "reason.skewness.log1p": (
        "Skewness = {skewness} (|skew| > {threshold}: highly skewed) and min = {min} >= 0, "
        "so log1p can compress the long tail."
    ),
    "reason.skewness.yeo_johnson": (
        "Skewness = {skewness} (|skew| > {threshold}: highly skewed) but min = {min} < 0; log1p "
        "only works on non-negative values, so Yeo-Johnson is used."
    ),
    # --- Trade-offs (one per option) ---
    "tradeoff.keep": "Keeps the column unchanged; the model sees it as-is.",
    "tradeoff.drop_column": "Removes the column; any information it holds is lost.",
    "tradeoff.extract": "Replaces the date with year, month, day and day-of-week columns.",
    "tradeoff.none": "Leaves the column untouched by this step.",
    "tradeoff.mean": "Fills gaps with the train mean; sensitive to long tails and extreme values.",
    "tradeoff.median": "Fills gaps with the train median; robust to extreme values.",
    "tradeoff.mode": "Fills gaps with the most frequent train value; can over-represent that value.",
    "tradeoff.constant": "Fills gaps with 0; simple, but 0 may be a misleading value.",
    "tradeoff.constant_missing": "Fills gaps with the category \"Missing\", so missingness becomes a signal.",
    "tradeoff.drop_rows": (
        "Removes the affected rows (missing value or outlier) from the train split only; test rows are kept "
        "(and still transformed) so the evaluation stays honest."
    ),
    "tradeoff.cap": "Clips values to the train fences; keeps every row but flattens the extremes.",
    "tradeoff.log1p": "Applies log(1 + x); strongly compresses a right tail, needs x >= 0.",
    "tradeoff.yeo_johnson": "Power transform fitted on train; works with negative values, harder to interpret.",
    "tradeoff.sqrt": "Applies the square root; a milder compression than log1p, needs x >= 0.",
    # --- Warnings ---
    "warning.stratify_fallback": (
        "Class '{cls}' has only {count} row(s), so a stratified split is impossible; "
        "a plain random split was used instead."
    ),
    # --- Errors ---
    "error.unreadable_file": "The file could not be read. Upload a CSV or Excel (.xlsx) file.",
    "error.unknown_sheet": "Sheet '{sheet}' does not exist in this workbook.",
}


def t(key: str, **kw) -> str:
    """Return the message for ``key`` with ``{placeholders}`` filled in.

    Raises ``KeyError`` for unknown keys so missing text is caught by tests
    rather than shown to the user as a raw key.
    """
    return MESSAGES[key].format(**kw)


def ui_labels() -> dict[str, str]:
    """All frontend labels (keys starting with ``ui.``)."""
    return {k: v for k, v in MESSAGES.items() if k.startswith("ui.")}
