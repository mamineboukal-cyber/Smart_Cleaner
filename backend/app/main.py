"""FastAPI routes. Run with: .venv/Scripts/python -m uvicorn app.main:app --reload

Flow: /upload -> /configure (dedupe, split, findings on train) -> /eda, /findings
-> /preview (per column) -> /apply -> /export (zip).
"""

from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app import session as store
from app.engine import run_rules
from app.i18n import t, ui_labels
from app.io import read_table
from app.preview import preview_column
from app.profiling import chart_data, column_stats, correlation_matrix
from app.report import build_report, build_zip
from app.split import prepare_and_split
from app.transforms import apply_all
from app.types import apply_type_overrides, infer_types, repair_excel_swapped_dates

COLUMN_TYPES = ("numeric", "categorical", "datetime")

app = FastAPI(title="Smart Cleaner")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class ConfigureRequest(BaseModel):
    session_id: str
    mode: Literal["supervised", "unsupervised"]
    target: str | None = None
    type_overrides: dict[str, str] = {}


class PreviewRequest(BaseModel):
    session_id: str
    column: str
    choices: dict[str, str] = {}


class ApplyRequest(BaseModel):
    session_id: str
    choices: dict[str, dict[str, str]] = {}


def _configured(sid: str) -> store.Session:
    s = store.get(sid)
    if s.split is None:
        raise HTTPException(status_code=409, detail=t("error.not_configured"))
    return s


def _dataset_summary(s: store.Session) -> dict:
    sp = s.split
    return {
        "task": sp.task,
        "stratified": sp.stratified,
        "n_train": len(sp.train),
        "n_test": len(sp.test),
        "n_duplicates": sp.n_duplicates,
        "n_target_missing": sp.n_target_missing,
        "warnings": sp.warnings,
    }


@app.get("/labels")
def labels() -> dict:
    return ui_labels()


@app.post("/upload")
async def upload(file: UploadFile = File(...), sheet: str | None = Form(None)) -> dict:
    content = await file.read()
    filename = file.filename or "upload.csv"
    try:
        df, sheets = read_table(content, filename, sheet)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    df.columns = [str(c) for c in df.columns]
    if df.empty or df.shape[1] == 0:
        raise HTTPException(status_code=400, detail=t("error.empty_file"))
    # Parsing, like type inference: a per-cell format fix, not a statistic, so it runs before the split.
    df, repairs = repair_excel_swapped_dates(df)
    types = infer_types(df)
    chosen_sheet = (sheet or sheets[0]) if sheets else None
    sid = store.create(store.Session(raw=df, filename=filename, sheet=chosen_sheet, sheets=sheets,
                                     types=dict(types), inferred_types=types, repairs=repairs))
    return {"session_id": sid, "filename": filename, "sheets": sheets, "sheet": chosen_sheet,
            "columns": list(df.columns), "types": types, "n_rows": len(df), "repairs": repairs}


@app.post("/configure")
def configure(req: ConfigureRequest) -> dict:
    s = store.get(req.session_id)
    if req.mode == "supervised" and req.target not in s.raw.columns:
        raise HTTPException(status_code=400, detail=t("error.invalid_target"))
    bad = {v for v in req.type_overrides.values() if v not in COLUMN_TYPES}
    if bad:
        raise HTTPException(status_code=400, detail=t("error.invalid_type", type=", ".join(sorted(bad))))
    target = req.target if req.mode == "supervised" else None

    s.types = apply_type_overrides(s.inferred_types, req.type_overrides)
    s.mode, s.target = req.mode, target
    s.split = prepare_and_split(s.raw, req.mode, target)
    # Shown in the EDA banner and the report's Dataset sheet, with the split warnings.
    s.split.warnings[:0] = [t("warning.excel_dates_repaired", column=col, count=n) for col, n in s.repairs.items()]
    s.findings, s.stats = run_rules(s.split, s.types, target)
    s.result, s.choices = None, {}
    return _dataset_summary(s)


@app.get("/eda")
def eda(session_id: str) -> dict:
    s = _configured(session_id)
    train = s.split.train
    columns = []
    for col in train.columns:
        typ = s.types[col]
        stats = s.stats.get(col) or column_stats(train[col], typ)   # target: computed here
        columns.append({"name": col, "type": typ, "is_target": col == s.target,
                        "stats": stats, "chart": chart_data(train[col], typ)})
    numeric = [c for c in train.columns if s.types[c] == "numeric" and c != s.target]
    return {"columns": columns, "correlation": correlation_matrix(train, numeric),
            "dataset": _dataset_summary(s)}


@app.get("/findings")
def findings(session_id: str) -> dict:
    s = _configured(session_id)
    return {"findings": [f.to_dict() for f in s.findings]}


@app.post("/preview")
def preview(req: PreviewRequest) -> dict:
    s = _configured(req.session_id)
    if req.column not in s.split.train.columns or req.column == s.target:
        raise HTTPException(status_code=400, detail=t("error.unknown_column", column=req.column))
    return preview_column(s.split.train, req.column, s.types[req.column], req.choices)


@app.post("/apply")
def apply(req: ApplyRequest) -> dict:
    s = _configured(req.session_id)
    choices = {c: v for c, v in req.choices.items() if c in s.types and c != s.target}
    s.choices = choices
    s.result = apply_all(s.split, s.types, choices, s.target)
    r = s.result
    n_out = r.train.shape[1] - (1 if s.target is not None else 0)
    return {"n_train": len(r.train), "n_test": len(r.test), "n_columns_out": n_out,
            "rows_dropped_train": r.rows_dropped_train, "applied": r.applied,
            # Scaling recommendation recomputed after each column's earlier steps (as in the report).
            "scaling": {c: f.to_dict() for c, f in r.scaling_findings.items()}}


@app.get("/export")
def export(session_id: str) -> Response:
    s = _configured(session_id)
    if s.result is None:
        raise HTTPException(status_code=409, detail=t("error.not_applied"))
    meta = {"filename": s.filename, "mode": s.mode, "target": s.target, "sheet": s.sheet}
    report = build_report(meta, s.split, s.stats, s.types, s.findings, s.result)
    return Response(
        content=build_zip(s.result, report),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=smart_cleaner_export.zip"},
    )
