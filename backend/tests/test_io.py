import io

import pandas as pd
import pytest

from app.io import read_table


def _xlsx(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
    return buf.getvalue()


def test_reads_semicolon_csv_with_comma_decimal():
    df, sheets = read_table(b"a;b\n1,5;x\n2,5;y\n", "f.csv")
    assert list(df.columns) == ["a", "b"]
    assert df["a"].tolist() == [1.5, 2.5]
    assert sheets == []


def test_reads_comma_csv():
    df, _ = read_table(b"a,b\n1,x\n2,y\n", "f.csv")
    assert df.shape == (2, 2)


def test_reads_latin1_csv():
    df, _ = read_table("name,v\ncafé,1\n".encode("latin-1"), "f.csv")
    assert df["name"].iloc[0] == "café"


def test_excel_lists_sheets_and_reads_chosen_one():
    first = pd.DataFrame({"a": [1, 2]})
    second = pd.DataFrame({"b": [3, 4], "c": ["x", "y"]})
    df, sheets = read_table(_xlsx({"first": first, "second": second}), "f.xlsx", sheet="second")
    assert sheets == ["first", "second"]
    assert df["b"].tolist() == [3, 4] and df["c"].tolist() == ["x", "y"]


def test_excel_defaults_to_first_sheet():
    df, _ = read_table(_xlsx({"first": pd.DataFrame({"a": [1]}), "s2": pd.DataFrame({"b": [2]})}), "f.xlsx")
    assert list(df.columns) == ["a"]


def test_garbage_raises_value_error():
    with pytest.raises(ValueError):
        read_table(b"\x00\x01\x02", "f.xlsx")


def test_unknown_sheet_raises_value_error():
    with pytest.raises(ValueError):
        read_table(_xlsx({"first": pd.DataFrame({"a": [1]})}), "f.xlsx", sheet="nope")
