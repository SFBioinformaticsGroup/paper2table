"""
Generic module for reading any kind of
pdf document
"""

import logging
from typing import Callable, Optional, Protocol, Generator

import pandas as pd

from utils.normalize_name import normalize_name

from ..hints import parse_column_names_hints
from ..mapping import TableMapping, TablesMapping
from ..tables_reader import TablesReader
from ..tables_reader.dataframe import DataFrameTableReader, DataFrameTablesReader


class PDFTable(Protocol):
    def to_dataframe(
        self, column_names_hints: list[str], skip_first_row: bool
    ) -> pd.DataFrame: ...


class PDFPage:
    def extract_tables_candidates(
        self,
    ) -> Generator[tuple[str, list[PDFTable]], None, None]:
        yield ("default", self.extract_tables())

    def extract_tables(self) -> list[PDFTable]: ...

    @property
    def page_number(self) -> int: ...


class PDFDocument:
    """
    A base class for pdf documents
    """

    @property
    def page_count(self) -> int: ...

    @property
    def pages(self) -> list[PDFPage]: ...

    def page_at(self, index: int) -> PDFPage:
        return self.pages[index - 1]


_logger = logging.getLogger("pape2table")


def read_tables(
    pdf_path: str,
    read_document: Callable[[str], PDFDocument],
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:
    try:
        document = read_document(pdf_path)
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return DataFrameTablesReader(pdf_path, [])

    if mapping:
        tables = read_mapped_tables(pdf_path, mapping, document)
    else:
        tables = read_all_tables(pdf_path, column_names_hints, document)

    return DataFrameTablesReader(
        pdf_path, tables, citation=mapping.citation if mapping else None
    )


def read_mapped_tables(pdf_path: str, mapping: TablesMapping, document: PDFDocument):
    """
    Reads the tables described by schema
    """
    tables = []
    for table_mapping in mapping.tables:
        for page_number in range(table_mapping.first_page, table_mapping.last_page + 1):
            try:
                page = document.page_at(page_number)
            except IndexError:
                _logger.warning(
                    f"Page {page_number} in schema is out of bounds of {pdf_path}. Abort processing"
                )
                break

            candidates = page.extract_tables_candidates()
            last_error: Exception | None = None
            for strategy, extracted_tables in candidates:
                try:
                    dataframe = read_page_as_dataframe(
                        extracted_tables, table_mapping, page_number
                    )
                    tables.append(
                        DataFrameTableReader(
                            title=table_mapping.title,
                            page=page_number,
                            dataframe=dataframe,
                        )
                    )
                    last_error = None
                    break
                except Exception as e:
                    _logger.debug(
                        "Strategy %s failed when reading page %i", strategy, page_number
                    )
                    last_error = e

            if last_error:
                _logger.warning(
                    f"Couldn't read page {page_number} of {pdf_path}"
                    f" with strategy {strategy}: {last_error}"
                )

        break

    return tables


def read_page_as_dataframe(
    extracted_tables: list[PDFTable], table_mapping: TableMapping, page_number: int
):
    if not extracted_tables:
        raise ValueError("No tables were extracted")

    return read_table(
        table_fragment=extracted_tables[-1],
        table_mapping=table_mapping,
        page=page_number,
    )


def read_table(
    table_fragment: PDFTable,
    column_names_hints: list[str] = [],
    table_mapping: Optional[TableMapping] = None,
    page: Optional[int] = None,
) -> pd.DataFrame:
    skip_first_row = table_mapping is not None and (
        table_mapping.header_mode == "all_pages"
        or (
            table_mapping.header_mode == "first_page_only"
            and page == table_mapping.first_page
        )
    )

    dataframe: pd.DataFrame = table_fragment.to_dataframe(
        column_names_hints, skip_first_row
    )

    def index_renamer(column):
        return dataframe.columns.get_loc(column)

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

        dataframe = dataframe.rename(index_renamer, axis="columns")[
            selected_column_names
        ].rename(columns=renamer)

    dataframe.rename(columns=lambda column: normalize_name(str(column)), inplace=True)
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if isinstance(v, str) else v, row)
        )
    )

    return dataframe


def read_all_tables(
    pdf_path: str, column_names_hints: Optional[str], document: PDFDocument
):
    tables = []
    parsed_hints = (
        parse_column_names_hints(column_names_hints) if column_names_hints else []
    )
    for page in document.pages:
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
