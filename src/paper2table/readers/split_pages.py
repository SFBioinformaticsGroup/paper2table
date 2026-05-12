import os
import tempfile
import time
from typing import Callable, List, Tuple

import pymupdf

from .errors import PartialProcessingError
from ..tables_reader import TablesReader


def fix_page_numbers(table_dict: dict, actual_page: int) -> dict:
    corrected = dict(table_dict)
    if "table_fragments" in corrected:
        corrected["table_fragments"] = [
            {**frag, "page": actual_page} for frag in corrected["table_fragments"]
        ]
    return corrected


class SplitPagesTablesReader:
    def __init__(self, filename: str, tables: list, citation):
        self.filename = filename
        self._tables = tables
        self._citation = citation

    @property
    def tables(self):
        return self._tables

    @property
    def citation(self):
        return self._citation

    def to_dict(self):
        return {
            "tables": self._tables,
            "citation": self._citation,
            "metadata": {"filename": self.filename},
        }


def read_tables_from_pages(
    pdf_path: str, page_results: list[tuple[int, TablesReader]]
) -> SplitPagesTablesReader:
    all_tables = []
    citation = None
    for page_num, reader in page_results:
        reader_dict = reader.to_dict()
        for table in reader_dict.get("tables", []):
            all_tables.append(fix_page_numbers(table, page_num))
        if citation is None and reader_dict.get("citation"):
            citation = reader_dict["citation"]
    return SplitPagesTablesReader(
        filename=os.path.basename(pdf_path),
        tables=all_tables,
        citation=citation,
    )


def write_tmp_page_file(doc, page_number):
    page_doc = pymupdf.open()
    page_doc.insert_pdf(doc, from_page=page_number, to_page=page_number)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    page_doc.save(tmp.name)
    page_doc.close()
    tmp.close()
    return tmp


def read_tables(
    pdf_path: str, page_reader: Callable[[str], TablesReader], sleep: int = 0
) -> TablesReader:
    page_results: List[Tuple[int, TablesReader]] = []
    with pymupdf.open(pdf_path) as document:
        for i in range(document.page_count):
            page_num = i + 1
            time.sleep(sleep)
            tmp = write_tmp_page_file(document, i)
            try:
                result = page_reader(tmp.name)
                page_results.append((page_num, result))
            except Exception as e:
                partial = read_tables_from_pages(pdf_path, page_results)
                raise PartialProcessingError(page_num, partial, e) from e
            finally:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
    return read_tables_from_pages(pdf_path, page_results)
