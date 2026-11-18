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
    # --- UI: app shell and steps ---
    "ui.app.title": "Smart Cleaner",
    "ui.app.subtitle": "Prepare a dataset for machine learning, one justified step at a time.",
    "ui.app.steps": "Workflow steps",
    "ui.step.locked": "Analyse a file on the Import step first.",
    "ui.step.no_file": "No file yet",
    "ui.step.rows": "{n} rows",
    "ui.step.split": "{train} train, {test} test",
    "ui.step.findings": "{n} findings",
    "ui.step.applied": "Applied",
    "ui.step.not_applied": "Not applied yet",
    "ui.error.network": "The server could not be reached. Start the backend on port 8000, then try again.",
    "ui.error.title": "Something went wrong",
    "ui.dismiss": "Dismiss",
    "ui.missing_value": "–",
    # --- UI: Import tab ---
    "ui.import.heading": "Import and configure",
    "ui.import.file": "Dataset file",
    "ui.import.file_help": "CSV or Excel (.xlsx). Separators and decimal commas are detected automatically.",
    "ui.import.uploading": "Reading the file…",
    "ui.import.sheet": "Sheet",
    "ui.import.sheet_help": "This workbook has several sheets. The analysis uses the one selected here.",
    "ui.import.summary": "{rows} rows and {columns} columns",
    "ui.import.mode": "Learning mode",
    "ui.mode.supervised": "Supervised",
    "ui.mode.supervised_help": "Predict a target column. Classification targets get a stratified split.",
    "ui.mode.unsupervised": "Unsupervised",
    "ui.mode.unsupervised_help": "No target column. The data gets a plain random split.",
    "ui.import.target": "Target column",
    "ui.import.target_placeholder": "Select the column to predict",
    "ui.import.target_tag": "Target",
    "ui.import.types": "Column types",
    "ui.import.types_help": "Inferred from the data. Correct a type here if it is wrong; the analysis uses your choice.",
    "ui.import.column": "Column",
    "ui.import.inferred": "Inferred",
    "ui.import.type": "Type used",
    "ui.import.analyse": "Analyse",
    "ui.import.analysing": "Analysing…",
    "ui.import.need_target": "Select a target column to analyse in supervised mode.",
    "ui.import.empty": "Choose a CSV or Excel file to start.",
    # --- UI: shared vocabulary ---
    "ui.type.numeric": "Numeric",
    "ui.type.categorical": "Categorical",
    "ui.type.datetime": "Date/time",
    "ui.task.classification": "Classification",
    "ui.task.regression": "Regression",
    "ui.task.none": "None (unsupervised)",
    "ui.severity.info": "Info",
    "ui.severity.warning": "Warning",
    "ui.severity.error": "Error",
    "ui.rule.duplicates": "Duplicate rows",
    "ui.rule.constant": "Constant or near-constant",
    "ui.rule.id_like": "Identifier-like",
    "ui.rule.free_text": "Free text",
    "ui.rule.datetime": "Date/time",
    "ui.rule.missing": "Missing values",
    "ui.rule.outliers": "Outliers",
    "ui.rule.skewness": "Skewness",
    "ui.rule.encoding": "Encoding",
    "ui.rule.scaling": "Scaling",
    "ui.rule.correlation": "High correlation",
    "ui.rule.imbalance": "Class imbalance",
    "ui.rule.analysis_failed": "Analysis failed",
    "ui.option.none": "None",
    "ui.option.keep": "Keep",
    "ui.option.drop_column": "Drop column",
    "ui.option.drop_rows": "Drop rows (train only)",
    "ui.option.mean": "Mean",
    "ui.option.median": "Median",
    "ui.option.mode": "Mode",
    "ui.option.constant": "Constant (0)",
    "ui.option.constant_missing": "Category \"Missing\"",
    "ui.option.cap": "Cap at IQR fences",
    "ui.option.log1p": "log1p",
    "ui.option.yeo_johnson": "Yeo-Johnson",
    "ui.option.sqrt": "Square root",
    "ui.option.onehot": "One-hot",
    "ui.option.ordinal": "Ordinal",
    "ui.option.frequency": "Frequency",
    "ui.option.standard": "StandardScaler",
    "ui.option.minmax": "MinMaxScaler",
    "ui.option.robust": "RobustScaler",
    "ui.option.extract": "Extract date parts",
    "ui.option.remove": "Remove",
    "ui.option.class_weight_balanced": "class_weight=\"balanced\"",
    "ui.stat.missing_pct": "Missing %",
    "ui.stat.n_unique": "Unique",
    "ui.stat.mean": "Mean",
    "ui.stat.std": "Std",
    "ui.stat.min": "Min",
    "ui.stat.max": "Max",
    "ui.stat.skewness": "Skewness",
    "ui.stat.outlier_pct": "Outlier %",
    "ui.stat.top_freq_pct": "Top value %",
    "ui.stat.mean_length": "Mean length",
    "ui.split.stratified": "Stratified 80/20",
    "ui.split.random": "Random 80/20",
    "ui.chart.rows": "Rows",
    "ui.chart.r": "Pearson r",
    "ui.chart.empty": "No values to plot.",
    # --- UI: EDA tab ---
    "ui.eda.heading": "Exploratory analysis",
    "ui.eda.intro": (
        "Every figure here is computed on the train split (80%), the same rows the transformations "
        "will be fitted on. Duplicates were removed before the split."
    ),
    "ui.eda.dataset": "Dataset",
    "ui.eda.file": "File",
    "ui.eda.task": "Task",
    "ui.eda.split": "Split",
    "ui.eda.train": "Train rows",
    "ui.eda.test": "Test rows",
    "ui.eda.duplicates": "Duplicate rows removed",
    "ui.eda.target_missing": "Rows without a target removed",
    "ui.eda.class_ratio": "Smallest / largest class",
    "ui.eda.class_counts": "Class counts (train)",
    "ui.eda.stats": "Column statistics",
    "ui.eda.stats_help": "Select a column header to sort. Highlighted cells have missing values.",
    "ui.eda.column": "Column",
    "ui.eda.type": "Type",
    "ui.eda.distributions": "Distributions",
    "ui.eda.distributions_help": (
        "Numeric columns: histogram with up to 30 bins. Other columns: the most frequent values, "
        "with the rest grouped as Other."
    ),
    "ui.eda.correlation": "Correlation between numeric columns",
    "ui.eda.correlation_help": (
        "Pearson r on the train split, target excluded. Blue is negative, red is positive, grey is "
        "no linear relation. Pairs above |r| = 0.95 are flagged on the Preprocessing step."
    ),
    # --- UI: Preprocessing tab ---
    "ui.prep.heading": "Preprocessing & cleaning",
    "ui.prep.intro": (
        "For each column: what was detected on the train split, the recommended step with the numbers "
        "behind it, and every alternative. Choose one option per finding. Nothing is applied until "
        "the Execute & export step."
    ),
    "ui.prep.reset": "Reset to recommendations",
    "ui.prep.dataset_findings": "Dataset-level findings",
    "ui.prep.columns": "Columns",
    "ui.prep.only_warnings": "Only columns with warnings",
    "ui.prep.no_match": "No column has a warning.",
    "ui.prep.n_findings": "{n} findings",
    "ui.prep.no_findings_short": "No findings",
    "ui.prep.changed": "Changed",
    "ui.prep.no_anomaly": "No anomaly detected. This column passes through unchanged.",
    "ui.prep.recommendation": "Recommendation:",
    "ui.prep.recommended": "Recommended",
    "ui.prep.your_choice": "Your choice for {rule}",
    "ui.prep.scaling_updated": (
        "Recomputed by the last preview on this column after your earlier choices (scaling runs last)."
    ),
    "ui.prep.preview_title": "Before and after",
    "ui.prep.preview_help": "Runs this column's chosen steps in pipeline order, fitted on the train split.",
    "ui.prep.preview": "Preview",
    "ui.prep.previewing": "Computing…",
    "ui.prep.preview_stale": "Your choices changed since this preview. Preview again to update it.",
    "ui.prep.before": "Before (raw train)",
    "ui.prep.after": "After",
    "ui.prep.before_short": "Before",
    "ui.prep.after_short": "After",
    "ui.prep.after_column": "Output column",
    "ui.prep.after_many": "This step outputs {n} columns. Pick one above to inspect it.",
    "ui.prep.dropped": "The column is dropped, so there is nothing to show after.",
    "ui.prep.rows_dropped": "{n} train rows are dropped by your choices. Test rows are kept and transformed.",
    "ui.prep.stat": "Statistic",
    "ui.eda.no_correlation": "There are fewer than two numeric columns, so there is no correlation matrix.",
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
    "reason.encoding.onehot": (
        "{n_unique} categories (<= {threshold}): one-hot encoding adds one binary column per "
        "category without implying an order."
    ),
    "reason.encoding.frequency": (
        "{n_unique} categories (> {threshold}): one-hot would add too many sparse columns, so "
        "frequency encoding keeps a single column, fitted on train counts."
    ),
    "reason.scaling.robust": (
        "{outlier_pct}% of values are outliers (> {threshold}%). RobustScaler uses the median and "
        "IQR, which stay stable when that many values are extreme."
    ),
    "reason.scaling.standard": (
        "{outlier_pct}% of values are outliers (<= {threshold}%). Standardising to mean 0, std 1 "
        "is the default."
    ),
    "reason.duplicates.remove": (
        "{n_duplicates} exact duplicate row(s) ({duplicate_pct}% of the file). A duplicated row "
        "could land in both train and test, which leaks test answers into training."
    ),
    "reason.correlation.drop_column": (
        "'{drop}' and '{keep}' have |Pearson r| = {r} (threshold: > {threshold}). They carry almost "
        "the same information; '{drop}' is dropped (more missing values, or later column on a tie)."
    ),
    "reason.imbalance.class_weight_balanced": (
        "Smallest / largest class = {ratio} (threshold: < {threshold}; smallest class: '{smallest}'). "
        "A model could score well by ignoring the rare class; class weights correct this without "
        "inventing rows. Recorded only: no resampling is done."
    ),
    "reason.imbalance.none": (
        "Smallest / largest class = {ratio} (>= {threshold}; smallest class: '{smallest}'). "
        "The classes are balanced enough."
    ),
    "reason.analysis_failed": (
        "The analysis of this column failed ({error}). No transformation is recommended; the rest "
        "of the dataset was analysed normally."
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
    "tradeoff.onehot": "One binary column per category; no false order, but many columns if categories are many.",
    "tradeoff.ordinal": "One integer per category; compact, but implies an order that may not exist.",
    "tradeoff.frequency": "Replaces each category by its train frequency; one column, but equal-frequency categories collide.",
    "tradeoff.standard": "Mean 0, std 1 (train); sensitive to extreme values.",
    "tradeoff.minmax": "Rescales to [0, 1] (train min/max); one extreme value squashes the rest.",
    "tradeoff.robust": "Centres on the median and divides by the IQR (train); stable with outliers.",
    "tradeoff.remove": (
        "Duplicates are removed before the train/test split (otherwise one copy could be in each), "
        "so this step is not optional."
    ),
    "tradeoff.class_weight_balanced": (
        "Recorded for the model: use class_weight=\"balanced\". No rows are added or removed."
    ),
    # --- Excel report ---
    "report.sheet.dataset": "Dataset",
    "report.sheet.features": "Features",
    "report.sheet.correlations": "Correlations",
    "report.dataset.label": "Item",
    "report.dataset.value": "Value",
    "report.dataset.file": "File",
    "report.dataset.sheet": "Sheet",
    "report.dataset.mode": "Learning mode",
    "report.dataset.target": "Target",
    "report.dataset.task": "Task",
    "report.dataset.rows_raw": "Rows (raw)",
    "report.dataset.duplicates": "Duplicate rows removed",
    "report.dataset.target_missing": "Rows with missing target removed",
    "report.dataset.split": "Split method",
    "report.dataset.train_size": "Train size",
    "report.dataset.test_size": "Test size",
    "report.dataset.rows_dropped": "Train rows dropped",
    "report.dataset.warnings": "Warnings",
    "report.dataset.class_counts": "Class counts (train)",
    "report.dataset.class_ratio": "Smallest / largest class",
    "report.dataset.imbalance": "Imbalance recommendation",
    "report.split.stratified": "Stratified 80/20",
    "report.split.random": "Random 80/20",
    "report.features.column": "Column",
    "report.features.type": "Type",
    "report.features.missing_pct": "Missing %",
    "report.features.n_unique": "Unique values",
    "report.features.mean": "Mean",
    "report.features.std": "Std",
    "report.features.min": "Min",
    "report.features.max": "Max",
    "report.features.skewness": "Skewness",
    "report.features.outlier_pct": "Outlier %",
    "report.features.anomalies": "Anomalies detected",
    "report.features.recommendations": "Recommendations (with reasons)",
    "report.features.alternatives": "Alternatives",
    "report.features.applied": "Applied",
    "report.features.match": "Matches recommendation",
    "report.correlations.column_a": "Column A",
    "report.correlations.column_b": "Column B",
    "report.correlations.r": "Pearson r",
    "report.correlations.dropped": "Dropped column",
    # --- Warnings ---
    "warning.stratify_fallback": (
        "Class '{cls}' has only {count} row(s), so a stratified split is impossible; "
        "a plain random split was used instead."
    ),
    # --- Errors ---
    "error.unreadable_file": "The file could not be read. Upload a CSV or Excel (.xlsx) file.",
    "error.unknown_sheet": "Sheet '{sheet}' does not exist in this workbook.",
    "error.empty_file": "The file contains no data.",
    "error.invalid_target": "Supervised learning needs a target column that exists in the file.",
    "error.invalid_type": "Unknown column type: {type}. Use numeric, categorical or datetime.",
    "error.unknown_column": "Column '{column}' cannot be previewed.",
    "error.unknown_session": "This session does not exist (the server may have restarted). Upload the file again.",
    "error.not_configured": "Configure the learning mode first.",
    "error.not_applied": "Apply the transformations before exporting.",
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
