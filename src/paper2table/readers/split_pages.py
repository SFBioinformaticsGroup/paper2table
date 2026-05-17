import os
import tempfile
import time
from typing import Callable, List, Optional, Tuple

import logging
import pymupdf

from .errors import PartialProcessingError
from ..tables_reader import TablesReader

_logger = logging.getLogger("pape2table")


def fix_page_numbers(table_dict: dict, page_offset: int) -> dict:
    """
    Add page_offset to every fragment's page number
    to convert temp-PDF pages to physical pages.
    """
    corrected = dict(table_dict)
    if "table_fragments" in corrected:
        corrected["table_fragments"] = [
            {**fragment, "page": fragment["page"] + page_offset}
            for fragment in corrected["table_fragments"]
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
    """
    Merge per-batch results into a single reader,
    correcting page numbers via their offsets.
    """
    all_tables = []
    citation = None
    for page_offset, reader in page_results:
        reader_dict = reader.to_dict()
        for table in reader_dict.get("tables", []):
            all_tables.append(fix_page_numbers(table, page_offset))
        if citation is None and reader_dict.get("citation"):
            citation = reader_dict["citation"]
    return SplitPagesTablesReader(
        filename=os.path.basename(pdf_path),
        tables=all_tables,
        citation=citation,
    )


def write_tmp_page_file(doc, page_indices: list[int]) -> str:
    """
    Write the given 0-indexed pages from doc to
    a temporary PDF and return its path.
    """
    with pymupdf.open() as page_doc:
        for i in page_indices:
            page_doc.insert_pdf(doc, from_page=i, to_page=i)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_name = tmp.name
        page_doc.save(tmp_name)
    return tmp_name


def read_tables(
    pdf_path: str,
    page_reader: Callable[[str], TablesReader],
    sleep: int = 0,
    page_range: Optional[Tuple[int, int]] = None,
    page_size: Optional[int] = None,
) -> TablesReader:
    """
    Call page_reader on batches of pages, reassigning physical page numbers in the output.

    Pass-through to page_reader(pdf_path) when both page_range and page_size are unset.
    page_size=None or page_size<0 means no batching (all selected pages in one call).
    """

    if page_size is not None and page_size < 1:
        raise ValueError(f"Page size {page_size} must be positive")

    if page_range is None and page_size is None:
        return page_reader(pdf_path)

    page_results: List[Tuple[int, TablesReader]] = []
    with pymupdf.open(pdf_path) as document:
        all_indices = list(range(document.page_count))
        selected = [
            i
            for i in all_indices
            if page_range is None or page_range[0] <= i + 1 <= page_range[1]
        ]

        if page_size is None:
            batches = [selected] if selected else []
        else:
            batches = [
                selected[i : i + page_size] for i in range(0, len(selected), page_size)
            ]

        for batch in batches:
            _logger.debug("Reading pages %s from %s", batch, pdf_path)
            time.sleep(sleep)
            tmp_path = write_tmp_page_file(document, batch)
            try:
                result = page_reader(tmp_path)
                page_results.append((batch[0], result))
            except BaseException as e:
                partial = read_tables_from_pages(pdf_path, page_results)
                raise PartialProcessingError(batch[0] + 1, partial, e) from e
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
    return read_tables_from_pages(pdf_path, page_results)
