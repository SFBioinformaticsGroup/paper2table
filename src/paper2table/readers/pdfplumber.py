import logging
from typing import Optional
import json

import pandas as pd
import pdfplumber
import pdfplumber.page


from . import document
from .utils import first_row_is_table_header, Row
from ..mapping import TablesMapping
from ..tables_reader import TablesReader
from .document import PDFDocument, PDFPage

_logger = logging.getLogger("pape2table")

type TableFragment = list[Row]


class PDFPlumberTable:
    rows: TableFragment

    def __init__(self, rows: TableFragment):
        self.rows = rows

    def to_dataframe(self, column_names_hints: list[str], skip_first_row: bool) -> pd.DataFrame:
        if skip_first_row or first_row_is_table_header(self.rows, column_names_hints):
            return pd.DataFrame(self.rows[1:], columns=self.rows[0])
        return pd.DataFrame(self.rows)


class PDFPlumberPage(PDFPage):
    def __init__(self, page: pdfplumber.page.Page):
        self.page = page

    def extract_tables_candidates(self):
        for settings in self.generate_pdfplumber_settings():
            settings_id = json.dumps(settings)
            yield (settings_id, self.extract_tables_with_settings(settings))

    def extract_tables(self) -> list[PDFPlumberTable]:
        tables = self.extract_tables_with_settings()
        _logger.debug("Extracted %i tables", len(tables))
        return tables

    def extract_tables_with_settings(self, settings = None):
        tables = self.page.extract_tables(settings)
        _logger.debug("Extracted %i tables", len(tables))
        return [PDFPlumberTable(table) for table in tables]

    def generate_pdfplumber_settings(self):
        for vertical_strategy in ["lines", "text"]:
            for horizontal_strategy in ["lines", "text"]:
                if vertical_strategy == "text":
                    for min_words in range(15, 0, -2):
                        yield {
                            "vertical_strategy": vertical_strategy,
                            "horizontal_strategy": horizontal_strategy,
                            "min_words_vertical": min_words,
                        }
                else:
                    yield {
                        "vertical_strategy": vertical_strategy,
                        "horizontal_strategy": horizontal_strategy,
                    }

    @property
    def page_number(self) -> int:
        return self.page.page_number


class PDFPlumberDocument(PDFDocument):
    _pdf: pdfplumber.pdf.PDF
    _pages: list[PDFPlumberPage]

    def __init__(self, pdf: pdfplumber.pdf.PDF):
        self._pdf = pdf
        self._pages = [PDFPlumberPage(page) for page in self._pdf.pages]

    @property
    def page_count(self) -> int:
        return len(self._pdf.pages)

    @property
    def pages(self) -> list[PDFPlumberPage]:
        return self._pages


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:
    return document.read_tables(
        pdf_path,
        column_names_hints=column_names_hints,
        mapping=mapping,
        read_document=lambda pdf_path: PDFPlumberDocument(
            pdfplumber.open(pdf_path, unicode_norm="NFKD", repair=True)
        ),
    )
