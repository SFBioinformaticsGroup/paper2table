from typing import Optional
import pandas as pd
from pdf2docx import Converter, Page
import logging

from paper2table.mapping import TablesMapping
from paper2table.readers import document
from paper2table.readers.utils import first_row_is_table_header
from paper2table.tables_reader import TablesReader


_logger = logging.getLogger(__name__)


class Pdf2DocxTable:
    def __init__(self, rows):
        self.table = rows

    def to_dataframe(self, column_names_hints: list[str]) -> pd.DataFrame:
        if first_row_is_table_header(self.rows, column_names_hints):
            return pd.DataFrame(self.rows[1:], columns=self.rows[0])
        return pd.DataFrame(self.rows)


class Pdf2DocxPage:
    page: Page
    index: int

    def __init__(self, index: int, page: Page):
        self.index = index
        self.page = page

    def extract_tables(self) -> list[Pdf2DocxTable]:
        tables = self.page.extract_tables()
        _logger.debug("Extracted %i tables", len(tables))
        return [Pdf2DocxTable(table) for table in tables]

    @property
    def page_number(self) -> int:
        return self.index


class Pdf2DocxDocument:
    document: Converter

    def __init__(self, document):
        self.document = document

    @property
    def page_count(self) -> int:
        return len(self.document.pages)

    @property
    def pages(self) -> list[Pdf2DocxPage]:
        return [
            Pdf2DocxPage(index, page) for index, page in enumerate(self.document.pages)
        ]


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:

    return document.read_tables(
        pdf_path,
        column_names_hints=column_names_hints,
        mapping=mapping,
        open=lambda pdf_path: Pdf2DocxDocument(open_pdf(pdf_path)),
    )


def open_pdf(pdf_path: str):
    with Converter(pdf_path) as converter:
        return converter
