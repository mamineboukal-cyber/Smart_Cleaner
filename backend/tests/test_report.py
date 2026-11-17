import io
import zipfile

import numpy as np
import openpyxl
import pandas as pd
import pytest

from app.engine import run_rules
from app.report import build_report, build_zip
from app.split import prepare_and_split
from app.transforms import apply_all
from app.types import infer_types


@pytest.fixture
def applied(mixed_df):
    df = mixed_df.assign(num_copy=mixed_df["sym"] * 2)   # one correlated pair
    types = infer_types(df)
    split = prepare_and_split(df, "supervised", "target")
    findings, stats = run_rules(split, types, "target")
    choices: dict[str, dict[str, str]] = {}
    for f in findings:
        if f.column and f.column != "target":
            choices.setdefault(f.column, {})[f.rule] = f.recommendation
    # as in the UI: scaling follows the recommendation recomputed after the earlier steps
    for col, f in apply_all(split, types, choices, "target").scaling_findings.items():
        choices.setdefault(col, {})["scaling"] = f.recommendation
    choices["sym"]["scaling"] = "minmax"                 # one deliberate override
    result = apply_all(split, types, choices, "target")
    meta = {"filename": "mixed.csv", "mode": "supervised", "target": "target", "sheet": None}
    report = build_report(meta, split, stats, types, findings, result)
    return dict(df=df, split=split, findings=findings, result=result,
                wb=openpyxl.load_workbook(io.BytesIO(report)))


def _features(wb) -> dict[str, dict]:
    rows = list(wb["Features"].iter_rows(values_only=True))
    header = rows[0]
    return {r[0]: dict(zip(header, r)) for r in rows[1:]}


def test_report_sheets_and_feature_rows(applied):
    wb = applied["wb"]
    assert wb.sheetnames == ["Dataset", "Features", "Correlations"]
    feats = _features(wb)
    assert set(feats) == set(applied["df"].columns) - {"target"}
    assert any("median" in str(c) for c in feats["num"].values())   # applied option visible


def test_report_matches_finding_numbers(applied):
    feats = _features(applied["wb"])
    skew = next(f for f in applied["findings"] if f.column == "num" and f.rule == "skewness")
    row = feats["num"]
    assert row["Skewness"] == skew.stats["skewness"]


def test_report_match_column(applied):
    feats = _features(applied["wb"])
    assert feats["num"]["Matches recommendation"] == "yes"
    assert feats["sym"]["Matches recommendation"] == "partial"
    assert feats["const_col"]["Matches recommendation"] == "yes"


def test_report_correlations_sheet(applied):
    rows = list(applied["wb"]["Correlations"].iter_rows(values_only=True))
    assert len(rows) == 2 and {rows[1][0], rows[1][1]} == {"sym", "num_copy"}
    assert rows[1][3] == "num_copy"


def test_report_dataset_sheet(applied):
    rows = dict(applied["wb"]["Dataset"].iter_rows(values_only=True))
    assert rows["File"] == "mixed.csv" and rows["Task"] == "classification"
    assert rows["Train size"] == len(applied["result"].train)
    assert "class_weight_balanced" in str(rows["Imbalance recommendation"])


def test_zip_contains_three_files(applied):
    data = build_zip(applied["result"], b"x")
    z = zipfile.ZipFile(io.BytesIO(data))
    assert sorted(z.namelist()) == ["report.xlsx", "test.csv", "train.csv"]
    train = pd.read_csv(z.open("train.csv"))
    assert len(train) == len(applied["result"].train)
