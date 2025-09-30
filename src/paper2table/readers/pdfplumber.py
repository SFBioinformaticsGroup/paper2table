import logging

import pandas as pd
import pdfplumber

from utils.normalize_name import normalize_name
from utils.tokenize_schema import tokenize_schema

from ..tables import Table, Tables
from ..tables_protocol import TablesProtocol

_logger = logging.getLogger(__name__)

type TableFragment = list[list[str | None]]


def parse_column_names_hints(hints: str) -> list[str]:
    return [normalize_name(hint) for hint in tokenize_schema(hints)]


def read_tables(pdf_path: str, column_names_hints: str) -> TablesProtocol:
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return Tables(pdf_path, [])

    tables = []
    parsed_hints = parse_column_names_hints(column_names_hints)
    for page in pdf.pages:
        try:
            table_fragments = page.extract_tables()
            for table_fragment in table_fragments:
                dataframe = read_table(
                    table_fragment if table_fragment else [],
                    column_names_hints=parsed_hints,
                )
                tables.append(Table(page.page_number, dataframe))
        except Exception as e:
            _logger.warning(f"Error reading page {page.page_number} of {pdf_path}: {e}")

    return Tables(pdf_path, tables)


def first_row_is_table_header(rows: TableFragment, column_names_hints: list[str]):
    return (
        rows
        and column_names_hints
        and any(normalize_name(key) in column_names_hints for key in rows[0])
    )


def to_dataframe(rows: TableFragment, column_names_hints: list[str]):
    if first_row_is_table_header(rows, column_names_hints):
        return pd.DataFrame(rows[1:], columns=rows[0])
    else:
        return pd.DataFrame(rows)


def read_table(
    table_fragment: TableFragment, column_names_hints: list[str]
) -> pd.DataFrame:
    dataframe = to_dataframe(table_fragment, column_names_hints)
    dataframe = dataframe.rename(columns=lambda column: normalize_name(str(column)))
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if type(v) == str else v, row)
        )
    )

    return dataframe
