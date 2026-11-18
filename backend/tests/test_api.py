import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def c() -> TestClient:
    return TestClient(app)


def _upload(c, content: bytes, name: str = "d.csv") -> str:
    r = c.post("/upload", files={"file": (name, content)})
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def test_labels(c):
    labels = c.get("/labels").json()
    assert labels["ui.tab.eda"] and all(k.startswith("ui.") for k in labels)


def test_upload_response(c, mixed_df_csv_bytes):
    up = c.post("/upload", files={"file": ("d.csv", mixed_df_csv_bytes)}).json()
    assert up["filename"] == "d.csv" and up["n_rows"] == 200 and up["sheets"] == []
    assert up["columns"][0] == "id_col" and up["types"]["num"] == "numeric"


def test_full_flow(c, mixed_df_csv_bytes):
    sid = _upload(c, mixed_df_csv_bytes)
    conf = c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "target"}).json()
    assert conf["stratified"] and conf["n_test"] > 0 and conf["task"] == "classification"

    eda = c.get("/eda", params={"session_id": sid})
    assert eda.status_code == 200
    eda = eda.json()
    assert {col["name"] for col in eda["columns"]} >= {"num", "cat"}
    assert eda["dataset"]["n_train"] == conf["n_train"] and "matrix" in eda["correlation"]

    fs = c.get("/findings", params={"session_id": sid}).json()["findings"]
    choices = {}
    for f in fs:
        if f["column"] and f["column"] != "target":
            choices.setdefault(f["column"], {})[f["rule"]] = f["recommendation"]
    pv = c.post("/preview", json={"session_id": sid, "column": "num", "choices": choices["num"]})
    assert pv.status_code == 200 and pv.json()["scaling"] is not None

    ap = c.post("/apply", json={"session_id": sid, "choices": choices})
    assert ap.status_code == 200
    ap = ap.json()
    assert ap["n_test"] == conf["n_test"] and ap["applied"]["num"]["missing"] == "median"
    # the scaling recommendation recomputed after the earlier steps, so the UI can match the report
    assert ap["scaling"]["num"]["rule"] == "scaling"

    z = c.get("/export", params={"session_id": sid})
    assert z.headers["content-type"] == "application/zip"
    assert "smart_cleaner_export.zip" in z.headers["content-disposition"]
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert sorted(names) == ["report.xlsx", "test.csv", "train.csv"]


def test_unsupervised_flow(c, mixed_df_csv_bytes):
    sid = _upload(c, mixed_df_csv_bytes)
    conf = c.post("/configure", json={"session_id": sid, "mode": "unsupervised"}).json()
    assert conf["task"] is None and not conf["stratified"]
    fs = c.get("/findings", params={"session_id": sid}).json()["findings"]
    assert not any(f["rule"] == "imbalance" for f in fs)


def test_export_before_apply_409(c, mixed_df_csv_bytes):
    sid = _upload(c, mixed_df_csv_bytes)
    c.post("/configure", json={"session_id": sid, "mode": "unsupervised"})
    assert c.get("/export", params={"session_id": sid}).status_code == 409


def test_steps_before_configure_409(c, mixed_df_csv_bytes):
    sid = _upload(c, mixed_df_csv_bytes)
    assert c.get("/findings", params={"session_id": sid}).status_code == 409


def test_unknown_session_404(c):
    assert c.get("/findings", params={"session_id": "nope"}).status_code == 404


def test_supervised_without_target_400(c, mixed_df_csv_bytes):
    sid = _upload(c, mixed_df_csv_bytes)
    r = c.post("/configure", json={"session_id": sid, "mode": "supervised"})
    assert r.status_code == 400 and r.json()["detail"]
    r = c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "missing_col"})
    assert r.status_code == 400


def test_type_override_changes_findings(c):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"pclass": rng.integers(1, 4, size=100), "y": rng.integers(0, 2, size=100)})
    sid = _upload(c, df.to_csv(index=False).encode())

    def rules():
        fs = c.get("/findings", params={"session_id": sid}).json()["findings"]
        return {f["rule"] for f in fs if f["column"] == "pclass"}

    c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "y"})
    assert "encoding" in rules() and "scaling" not in rules()
    c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "y",
                               "type_overrides": {"pclass": "numeric"}})
    assert "scaling" in rules() and "encoding" not in rules()


def test_unreadable_upload_400(c):
    r = c.post("/upload", files={"file": ("broken.xlsx", b"not an excel file")})
    assert r.status_code == 400 and "could not be read" in r.json()["detail"]


def test_cors_allows_vite(c):
    r = c.options("/labels", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_same_file_and_settings_give_identical_results(c, mixed_df_csv_bytes):
    """Two uploads of the same bytes with the same settings: same split, same EDA numbers,
    same findings and byte-identical exported train/test files."""
    def run():
        sid = _upload(c, mixed_df_csv_bytes)
        c.post("/configure", json={"session_id": sid, "mode": "supervised", "target": "target"})
        eda = c.get("/eda", params={"session_id": sid}).json()
        fs = c.get("/findings", params={"session_id": sid}).json()["findings"]
        choices = {}
        for f in fs:
            if f["column"] and f["column"] != "target":
                choices.setdefault(f["column"], {})[f["rule"]] = f["recommendation"]
        c.post("/apply", json={"session_id": sid, "choices": choices})
        z = zipfile.ZipFile(io.BytesIO(c.get("/export", params={"session_id": sid}).content))
        return eda, fs, z.read("train.csv"), z.read("test.csv")

    first, second = run(), run()
    assert first[0] == second[0]          # EDA stats, charts, correlation, split summary
    assert first[1] == second[1]          # findings
    assert first[2] == second[2] and first[3] == second[3]


def test_excel_swapped_dates_repaired_and_flagged(c):
    import datetime as dt
    rng = np.random.default_rng(0)
    true = [(int(rng.integers(1, 29)), int(rng.integers(7, 10))) for _ in range(200)]   # (day, month), Jul-Sep
    # What Excel leaves from "dd/mm/2025" text: days <= 12 become real dates with day and month swapped.
    dates = [dt.datetime(2025, day, month) if day <= 12 else f"{day:02d}/{month:02d}/2025" for day, month in true]
    df = pd.DataFrame({"date": pd.Series(dates, dtype=object), "y": rng.integers(0, 2, 200)})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    up = c.post("/upload", files={"file": ("f.xlsx", buf.getvalue())}).json()
    n_swapped = sum(isinstance(x, dt.datetime) for x in dates)
    assert up["repairs"] == {"date": n_swapped}
    conf = c.post("/configure", json={"session_id": up["session_id"], "mode": "supervised", "target": "y"}).json()
    assert any("date" in w and str(n_swapped) in w for w in conf["warnings"])
    chart = next(x for x in c.get("/eda", params={"session_id": up["session_id"]}).json()["columns"]
                 if x["name"] == "date")["chart"]
    assert chart["edges"][0] >= "2025-07-01" and chart["edges"][-1] <= "2025-10-01"   # July-September only
