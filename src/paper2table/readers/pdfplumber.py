import logging
from typing import Optional

import pandas as pd
import pdfplumber

from utils.columns_schema import tokenize_schema
from utils.normalize_name import normalize_name

from ..mapping import TableMapping, TablesMapping
from ..tables_reader import TablesReader
from ..tables_reader.dataframe import DataFrameTableReader, DataFrameTablesReader

_logger = logging.getLogger(__name__)

type TableFragment = list[list[str | None]]


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return DataFrameTablesReader(pdf_path, [])

    if mapping:
        tables = read_mapped_tables(pdf_path, mapping, pdf)
    else:
        tables = read_all_tables(pdf_path, column_names_hints, pdf)

    return DataFrameTablesReader(
        pdf_path, tables, citation=mapping.citation if mapping else None
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


def read_mapped_tables(pdf_path: str, mapping: TablesMapping, pdf: pdfplumber.PDF):
    """
    Reads the tables described by schema
    """
    tables = []
    for table_mapping in mapping.tables:
        for page in range(table_mapping.first_page, table_mapping.last_page + 1):
            if page > len(pdf.pages):
                _logger.warning(
                    f"Page {page} in schema is out of bonds of {pdf_path}. Abort processing"
                )
                break

            extracted_tables = pdf.pages[page - 1].extract_tables()
            if not extracted_tables:
                _logger.warning(f"Couldn't read tables in page {page} of {pdf_path}")
                continue

            try:
                dataframe = read_table(
                    table_fragment=extracted_tables[-1],
                    table_mapping=table_mapping,
                    page=page,
                )
                tables.append(
                    DataFrameTableReader(
                        title=table_mapping.title, page=page, dataframe=dataframe
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
    return pd.DataFrame(rows)


def read_table(
    table_fragment: TableFragment,
    column_names_hints: list[str] = [],
    table_mapping: Optional[TableMapping] = None,
    page: Optional[int] = None,
) -> pd.DataFrame:
    dataframe = to_dataframe(table_fragment, column_names_hints)

    if table_mapping is not None:
        selected_column_names = list(
            map(
                lambda mapping: mapping.from_column_number,
                table_mapping.column_mappings,
            )
        )
        renamer = {
            mapping.from_column_number: mapping.to_column_name
            for mapping in table_mapping.column_mappings
        }
        dataframe = dataframe[selected_column_names].rename(columns=renamer)
        if table_mapping.header_mode == "all_pages" or (
            table_mapping.header_mode == "first_page_only"
            and page == table_mapping.first_page
        ):
            dataframe.drop([0], inplace=True)

    dataframe.rename(columns=lambda column: normalize_name(str(column)), inplace=True)
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if isinstance(v, str) else v, row)
        )
    )

    return dataframe
