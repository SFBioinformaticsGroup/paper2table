import logging
from typing import Optional

import pandas as pd
from img2table.document import PDF
from img2table.ocr import TesseractOCR
from img2table.tables.objects.extraction import ExtractedTable

from paper2table.mapping import TablesMapping
from paper2table.readers import document
from paper2table.tables_reader import TablesReader


_logger = logging.getLogger(__name__)


class Img2TableTable:
    def __init__(self, table: ExtractedTable):
        self.table = table

    def to_dataframe(
        self, _column_names_hints: list[str], skip_first_row: bool
    ) -> pd.DataFrame:
        dataframe = self.table.df
        if skip_first_row:
            dataframe.drop([0], inplace=True)
        return dataframe


class Img2TablePage:
    page: int
    tables: list[ExtractedTable]

    def __init__(self, page: int, tables: list[ExtractedTable]):
        self.page = page
        self.tables = tables

    def extract_tables(self) -> list[Img2TableTable]:
        return [Img2TableTable(table) for table in self.tables]

    @property
    def page_number(self) -> int:
        return self.index


class Img2TableDocument:
    tables: dict[int, list[ExtractedTable]]

    def __init__(self, tables: dict[int, list[ExtractedTable]]):
        self.tables = tables

    @property
    def page_count(self) -> int:
        return len(self.tables)

    @property
    def pages(self) -> list[Img2TablePage]:
        return [Img2TablePage(page, tables) for page, tables in self.tables.items()]


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:

    return document.read_tables(
        pdf_path,
        column_names_hints=column_names_hints,
        mapping=mapping,
        read_document=lambda pdf_path: Img2TableDocument(open_pdf(pdf_path)),
    )


def open_pdf(pdf_path: str):
    ocr = TesseractOCR(n_threads=1, lang="eng")
    pdf = PDF(pdf_path, detect_rotation=True, pdf_text_extraction=True)
    extracted = pdf.extract_tables(
        ocr=ocr,
        implicit_rows=True,
        implicit_columns=True,
        borderless_tables=True,
        min_confidence=20,
    )
    return extracted
