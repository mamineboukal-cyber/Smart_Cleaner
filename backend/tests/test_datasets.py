"""Generality checks: the full flow on datasets the app was not designed around.

No network: scikit-learn ships iris, wine and diabetes; the Excel file is built here.
"""

import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.datasets import load_diabetes, load_iris, load_wine

from app.main import app


@pytest.fixture
def c() -> TestClient:
    return TestClient(app)


def _recommended_choices(findings: list[dict], target: str | None) -> dict:
    choices: dict = {}
    for f in findings:
        if f["column"] and f["column"] != target:
            choices.setdefault(f["column"], {})[f["rule"]] = f["recommendation"]
    return choices


def _full_flow(c, content: bytes, filename: str, mode: str, target: str | None, sheet: str | None = None):
    data = {"sheet": sheet} if sheet else {}
    up = c.post("/upload", files={"file": (filename, content)}, data=data)
    assert up.status_code == 200, up.text
    sid = up.json()["session_id"]
    conf = c.post("/configure", json={"session_id": sid, "mode": mode, "target": target})
    assert conf.status_code == 200, conf.text
    assert c.get("/eda", params={"session_id": sid}).status_code == 200
    findings = c.get("/findings", params={"session_id": sid}).json()["findings"]
    ap = c.post("/apply", json={"session_id": sid, "choices": _recommended_choices(findings, target)})
    assert ap.status_code == 200, ap.text
    export = c.get("/export", params={"session_id": sid})
    return conf.json(), findings, export


@pytest.mark.parametrize("loader,task", [(load_iris, "classification"), (load_wine, "classification"),
                                         (load_diabetes, "regression")])
def test_sklearn_datasets_full_flow(c, loader, task):
    df = loader(as_frame=True).frame
    conf, _, export = _full_flow(c, df.to_csv(index=False).encode(), "d.csv", "supervised", "target")
    assert conf["task"] == task and conf["stratified"] == (task == "classification")
    assert export.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(export.content))
    train = pd.read_csv(z.open("train.csv"))
    assert len(train) == conf["n_train"] and not train.drop(columns="target").isna().any().any()


def _multisheet_xlsx() -> bytes:
    rng = np.random.default_rng(0)
    n = 300
    words = ["customer", "called", "about", "a", "late", "delivery", "and", "asked", "for", "refund",
             "the", "parcel", "arrived", "damaged", "after", "two", "weeks", "of", "waiting"]
    # 120 distinct sentences, repeated: > 50 unique but < 95% unique, so prose rather than an ID
    pool = [" ".join(rng.choice(words, 12)) for _ in range(120)]
    notes = rng.choice(pool, n)
    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")
    visit = [d.strftime("%Y-%m-%d") if i % 10 < 6 else f"unknown {i}" for i, d in enumerate(dates)]  # 60% parse
    notes_df = pd.DataFrame({"note": notes, "visit": visit, "amount": rng.exponential(50, n)})
    other_df = pd.DataFrame({"x": range(10)})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        other_df.to_excel(w, sheet_name="other", index=False)
        notes_df.to_excel(w, sheet_name="notes", index=False)
    return buf.getvalue()


def test_multisheet_with_text_and_bad_dates(c):
    content = _multisheet_xlsx()
    up = c.post("/upload", files={"file": ("book.xlsx", content)}).json()
    assert up["sheets"] == ["other", "notes"] and up["columns"] == ["x"]   # first sheet by default

    _, findings, export = _full_flow(c, content, "book.xlsx", "unsupervised", None, sheet="notes")
    rules = {(f["column"], f["rule"]) for f in findings}
    assert ("note", "free_text") in rules and ("visit", "datetime") in rules
    assert export.status_code == 200
