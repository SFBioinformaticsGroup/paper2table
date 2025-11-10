import logging
from typing import Optional

import pandas as pd
import pdfplumber

from utils.normalize_name import normalize_name
from utils.tokenize_schema import tokenize_schema

from ..tables_reader.dataframe import DataFrameTableReader, DataFrameTablesReader
from ..tables_reader import TablesReader

_logger = logging.getLogger(__name__)

type TableFragment = list[list[str | None]]

type ColumnMappings = dict[int, str]


class TableSchema:
    title: str
    first_page: int
    last_page: int
    column_mappings: ColumnMappings


class TablesSchema:
    tables: list[TableSchema]
    citation: str


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    schema: Optional[TablesSchema] = None,
) -> TablesReader:
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return DataFrameTablesReader(pdf_path, [])

    tables = []
    if schema:
        for table_schema in schema.tables:
            for page in range(table_schema.first_page, table_schema.last_page + 1):
                table_fragment = pdf.pages[page].extract_tables()[-1]
                try:
                    dataframe = read_table(
                        table_fragment if table_fragment else [],
                        column_mappings=table_schema.column_mappings,
                    )
                    tables.append(
                        DataFrameTableReader(
                            title=table_schema.title, page=page, dataframe=dataframe
                        )
                    )
                except Exception as e:
                    _logger.warning(f"Error reading page {page} of {pdf_path}: {e}")
    else:
        parsed_hints = (
            parse_column_names_hints(column_names_hints) if column_names_hints else []
        )
        for page in pdf.pages:
            try:
                table_fragments = page.extract_tables()
                for table_fragment in table_fragments:
                    dataframe = read_table(
                        table_fragment if table_fragment else [],
                        column_names_hints=parsed_hints,
                    )
                    tables.append(DataFrameTableReader(page.page_number, dataframe))
            except Exception as e:
                _logger.warning(
                    f"Error reading page {page.page_number} of {pdf_path}: {e}"
                )

    return DataFrameTablesReader(pdf_path, tables)


def parse_column_names_hints(hints: str) -> list[str]:
    return [normalize_name(hint) for hint in tokenize_schema(hints)]


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
    table_fragment: TableFragment,
    column_names_hints: list[str],
    column_mappings: Optional[ColumnMappings] = None,
) -> pd.DataFrame:
    dataframe = to_dataframe(table_fragment, column_names_hints)

    if column_mappings is not None:
        dataframe = dataframe[column_mappings.keys()].rename(column_mappings)

    dataframe = dataframe.rename(columns=lambda column: normalize_name(str(column)))
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if type(v) == str else v, row)
        )
    )

    return dataframe
