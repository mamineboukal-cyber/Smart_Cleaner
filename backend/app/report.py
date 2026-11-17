"""Excel report (Dataset / Features / Correlations) and the zip export.

The report is built from the same ``Finding`` objects and the same applied
choices as the UI, so the numbers always match. For scaling it uses the
finding recomputed after the earlier steps (``result.scaling_findings``).
"""

import io
import zipfile

import pandas as pd
from openpyxl.styles import Alignment, Font

from app.findings import (
    ANALYSIS_FAILED, CORRELATION, DROP_COLUMN, DUPLICATES, IMBALANCE, KEEP, NONE, SCALING, Finding,
)
from app.i18n import t
from app.split import SplitResult
from app.transforms import ApplyResult

STAT_KEYS = ["missing_pct", "n_unique", "mean", "std", "min", "max", "skewness", "outlier_pct"]
WRAP_COLUMNS = ("anomalies", "recommendations", "alternatives", "applied")
COLUMN_WIDTHS = {"column": 22, "type": 12, "anomalies": 30, "recommendations": 80,
                 "alternatives": 45, "applied": 30, "match": 16}
NO_OP = (NONE, KEEP)


def _same(a: str, b: str) -> bool:
    return a == b or (a in NO_OP and b in NO_OP)


def match_status(recommended: dict[str, str], applied: dict[str, str]) -> str:
    """'yes', 'no' or 'partial': does what was applied follow the recommendations?"""
    drops = [r for r, o in applied.items() if o == DROP_COLUMN]
    if drops:   # the column is gone: only the dropping decision counts
        return "yes" if any(recommended.get(r) == DROP_COLUMN for r in drops) else "no"
    if DROP_COLUMN in recommended.values():
        return "no"   # a drop was recommended but the column was kept
    if not recommended:
        return "yes"
    hits = [_same(rec, applied.get(rule, NONE)) for rule, rec in recommended.items()]
    return "yes" if all(hits) else "no" if not any(hits) else "partial"


def _column_findings(findings: list[Finding], result: ApplyResult) -> dict[str, list[Finding]]:
    by_col: dict[str, list[Finding]] = {}
    for f in findings:
        if f.column is None or f.rule in (IMBALANCE, DUPLICATES):
            continue
        if f.rule == SCALING and f.column in result.scaling_findings:
            continue   # replaced by the recomputed finding below
        by_col.setdefault(f.column, []).append(f)
    for col, f in result.scaling_findings.items():
        by_col.setdefault(col, []).append(f)
    return by_col


def _dataset_sheet(meta: dict, split: SplitResult, findings: list[Finding], result: ApplyResult) -> pd.DataFrame:
    imbalance = next((f for f in findings if f.rule == IMBALANCE), None)
    rows = [
        (t("report.dataset.file"), meta.get("filename")),
        (t("report.dataset.sheet"), meta.get("sheet") or "-"),
        (t("report.dataset.mode"), meta.get("mode")),
        (t("report.dataset.target"), meta.get("target") or "-"),
        (t("report.dataset.task"), split.task or "-"),
        (t("report.dataset.rows_raw"), split.n_rows_raw),
        (t("report.dataset.duplicates"), split.n_duplicates),
        (t("report.dataset.target_missing"), split.n_target_missing),
        (t("report.dataset.split"), t("report.split.stratified") if split.stratified else t("report.split.random")),
        (t("report.dataset.train_size"), len(result.train)),
        (t("report.dataset.test_size"), len(result.test)),
        (t("report.dataset.rows_dropped"), result.rows_dropped_train),
        (t("report.dataset.warnings"), "\n".join(split.warnings) or "-"),
    ]
    if imbalance is not None:
        rows += [
            (t("report.dataset.class_counts"), imbalance.stats["class_counts"]),
            (t("report.dataset.class_ratio"), imbalance.stats["ratio"]),
            (t("report.dataset.imbalance"), f"{imbalance.recommendation} — {imbalance.reason}"),
        ]
    return pd.DataFrame(rows, columns=[t("report.dataset.label"), t("report.dataset.value")])


def _features_sheet(stats: dict[str, dict], types: dict[str, str], findings: list[Finding],
                    result: ApplyResult) -> pd.DataFrame:
    by_col = _column_findings(findings, result)
    records = []
    for col in stats:
        fs = by_col.get(col, [])
        applied = result.applied.get(col, {})
        recommended = {f.rule: f.recommendation for f in fs if f.rule != ANALYSIS_FAILED}
        st = stats[col]
        record = {"column": col, "type": types.get(col)}
        record.update({k: st.get(k) for k in STAT_KEYS})
        record.update({
            "anomalies": "; ".join(f.rule for f in fs),
            "recommendations": "\n".join(f"{f.rule}: {f.recommendation} — {f.reason}" for f in fs),
            "alternatives": "\n".join(f"{f.rule}: {', '.join(a.option for a in f.alternatives)}" for f in fs),
            "applied": "\n".join(f"{r}: {o}" for r, o in applied.items()) or NONE,
            "match": match_status(recommended, applied),
        })
        records.append(record)
    df = pd.DataFrame(records, columns=["column", "type", *STAT_KEYS, *WRAP_COLUMNS, "match"])
    return df.rename(columns={c: t(f"report.features.{c}") for c in df.columns})


def _correlations_sheet(findings: list[Finding], result: ApplyResult) -> pd.DataFrame:
    rows = []
    for f in findings:
        if f.rule != CORRELATION:
            continue
        dropped = f.column if result.applied.get(f.column, {}).get(CORRELATION) == DROP_COLUMN else "-"
        rows.append((f.stats["other"], f.column, f.stats["r"], dropped))
    keys = ["column_a", "column_b", "r", "dropped"]
    return pd.DataFrame(rows, columns=[t(f"report.correlations.{k}") for k in keys])


def _format(ws, widths: list[int], wrap_from_header: set[str]) -> None:
    for i, cell in enumerate(ws[1]):
        cell.font = Font(bold=True)
        letter = cell.column_letter
        ws.column_dimensions[letter].width = widths[i] if i < len(widths) else 14
        if cell.value in wrap_from_header:
            for row in ws.iter_rows(min_row=2, min_col=i + 1, max_col=i + 1):
                row[0].alignment = Alignment(wrap_text=True, vertical="top")


def build_report(meta: dict, split: SplitResult, stats: dict[str, dict], types: dict[str, str],
                 findings: list[Finding], result: ApplyResult) -> bytes:
    sheets = {
        t("report.sheet.dataset"): _dataset_sheet(meta, split, findings, result),
        t("report.sheet.features"): _features_sheet(stats, types, findings, result),
        t("report.sheet.correlations"): _correlations_sheet(findings, result),
    }
    feature_widths = [COLUMN_WIDTHS["column"], COLUMN_WIDTHS["type"], *[11] * len(STAT_KEYS),
                      *[COLUMN_WIDTHS[c] for c in WRAP_COLUMNS], COLUMN_WIDTHS["match"]]
    wrap_headers = {t(f"report.features.{c}") for c in WRAP_COLUMNS} | {t("report.dataset.value")}
    widths = {
        t("report.sheet.dataset"): [36, 100],
        t("report.sheet.features"): feature_widths,
        t("report.sheet.correlations"): [22, 22, 10, 22],
    }
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            _format(writer.sheets[name], widths[name], wrap_headers)
    return buf.getvalue()


def build_zip(result: ApplyResult, report_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("train.csv", result.train.to_csv(index=False))
        z.writestr("test.csv", result.test.to_csv(index=False))
        z.writestr("report.xlsx", report_bytes)
    return buf.getvalue()
