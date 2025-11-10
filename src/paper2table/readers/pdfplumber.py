import logging
from typing import Literal, Optional

import pandas as pd
import pdfplumber
from pydantic import BaseModel

from utils.normalize_name import normalize_name
from utils.tokenize_schema import tokenize_schema

from ..tables_reader.dataframe import DataFrameTableReader, DataFrameTablesReader
from ..tables_reader import TablesReader

_logger = logging.getLogger(__name__)

type TableFragment = list[list[str | None]]

type ColumnMappings = dict[int, str]


class TableSchema(BaseModel):
    """
    Instructions for read_table
    about how to read a table.
    """

    title: str

    header_mode: Literal["all_pages", "first_page_only", "none"]

    first_page: int
    """
    1-based first page number where table is allocated
    """

    last_page: int
    """
    1-based last page number where table is allocated
    """

    column_mappings: ColumnMappings
    """
    Mappings that go from original column number
    to desired column name
    """


class TablesSchema(BaseModel):
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

    if schema:
        tables = read_schema_tables(pdf_path, schema, pdf)
    else:
        tables = read_all_tables(pdf_path, column_names_hints, pdf)

    return DataFrameTablesReader(
        pdf_path, tables, citation=schema.citation if schema else None
    )


def read_all_tables(
    pdf_path: str, column_names_hints: Optional[str], pdf: pdfplumber.PDF
):
    tables = []
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
            _logger.warning(f"Error reading page {page.page_number} of {pdf_path}: {e}")
    return tables


def read_schema_tables(pdf_path: str, schema: TablesSchema, pdf: pdfplumber.PDF):
    """
    Reads the tables described by schema
    """
    tables = []
    for table_schema in schema.tables:
        for page in range(table_schema.first_page, table_schema.last_page + 1):
            if page > len(pdf.pages):
                _logger.warning(
                    f"Page {page} in schema is out of bonds of {pdf_path}. Abort processing"
                )
                break

            table_fragment = pdf.pages[page - 1].extract_tables()[-1]
            try:
                dataframe = read_table(
                    table_fragment if table_fragment else [],
                    table_schema=table_schema,
                    page=page,
                )
                tables.append(
                    DataFrameTableReader(
                        title=table_schema.title, page=page, dataframe=dataframe
                    )
                )
            except Exception as e:
                _logger.warning(f"Error reading page {page} of {pdf_path}: {e}")
    return tables


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
    column_names_hints: list[str] = [],
    table_schema: Optional[TableSchema] = None,
    page: Optional[int] = None,
) -> pd.DataFrame:
    dataframe = to_dataframe(table_fragment, column_names_hints)

    if table_schema is not None:
        selected_column_names = list(table_schema.column_mappings.keys())
        renamer = {(key): value for key, value in table_schema.column_mappings.items()}
        dataframe = dataframe[selected_column_names].rename(columns=renamer)
        if table_schema.header_mode == "all_pages" or (
            table_schema.header_mode == "first_page_only"
            and page == table_schema.first_page
        ):
            dataframe.drop([0], inplace=True)

    dataframe.rename(columns=lambda column: normalize_name(str(column)), inplace=True)
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if type(v) == str else v, row)
        )
    )

    return dataframe
