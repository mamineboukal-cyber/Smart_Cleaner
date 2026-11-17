"""Reading uploaded CSV / Excel files into a DataFrame."""

import csv
import io

import pandas as pd

from app.i18n import t

EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm")
CSV_DELIMITERS = ",;\t|"


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(t("error.unreadable_file"))


def _sniff_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:65536], delimiters=CSV_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _read_csv(content: bytes) -> pd.DataFrame:
    text = _decode(content)
    sep = _sniff_delimiter(text)
    # European CSVs use ';' as separator precisely because ',' is the decimal mark.
    decimal = "," if sep == ";" else "."
    return pd.read_csv(io.StringIO(text), sep=sep, decimal=decimal)


def read_table(content: bytes, filename: str, sheet: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Parse an uploaded file.

    Returns the DataFrame and the list of sheet names (empty for CSV).
    For Excel, ``sheet`` selects the sheet (first sheet by default).
    Raises ``ValueError`` with a user-facing message when the file can't be read.
    """
    if not filename.lower().endswith(EXCEL_EXTENSIONS):
        try:
            return _read_csv(content), []
        except Exception as e:  # any parser failure becomes a user-facing message
            raise ValueError(t("error.unreadable_file")) from e

    try:
        book = pd.ExcelFile(io.BytesIO(content))
    except Exception as e:
        raise ValueError(t("error.unreadable_file")) from e
    sheets = [str(s) for s in book.sheet_names]
    chosen = sheet if sheet is not None else sheets[0]
    if chosen not in sheets:
        raise ValueError(t("error.unknown_sheet", sheet=chosen))
    try:
        return pd.read_excel(book, sheet_name=chosen), sheets
    except Exception as e:
        raise ValueError(t("error.unreadable_file")) from e
