"""Read CSV and Excel files into pandas DataFrames."""

from __future__ import annotations

import csv
import io
import pathlib

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xls", ".xlsx"}


def read_file(file_path: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    Handles:
    - CSV with auto-detected delimiter (comma, tab, semicolon, pipe)
    - XLS via xlrd
    - XLSX via openpyxl
    - Encoding fallback: utf-8 → latin-1
    - Aggressive date parsing
    """
    path = pathlib.Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext in (".xls", ".xlsx"):
        return _read_excel(path, ext)
    return _read_csv(path)


def _read_csv(path: pathlib.Path) -> pd.DataFrame:
    """Read CSV with auto-detected delimiter and encoding."""
    content = _read_with_encoding(path)
    delimiter = _detect_delimiter(content)

    df = pd.read_csv(
        io.StringIO(content),
        sep=delimiter,
        parse_dates=True,
        on_bad_lines="warn",
    )
    return df


def _read_excel(path: pathlib.Path, ext: str) -> pd.DataFrame:
    """Read XLS or XLSX file."""
    engine = "xlrd" if ext == ".xls" else "openpyxl"
    df = pd.read_excel(path, engine=engine)
    return df


def _read_with_encoding(path: pathlib.Path) -> str:
    """Try utf-8 first, fall back to latin-1."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError(f"Could not decode {path} with utf-8 or latin-1")


def _detect_delimiter(content: str) -> str:
    """Detect CSV delimiter from first few lines."""
    sample = content[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        return ","
