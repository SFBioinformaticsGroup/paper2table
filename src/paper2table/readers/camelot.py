import logging

import camelot

from ..tables_reader.dataframe import DataFrameTableReader, DataFrameTablesReader
from ..tables_reader import TablesReader

_logger = logging.getLogger(__name__)


def read_tables(pdf_path: str) -> TablesReader:
    try:
        camelot_tables = camelot.read_pdf(
            pdf_path, suppress_stdout=True, flavor="hybrid", pages="all"
        )
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return DataFrameTablesReader(pdf_path, [])

    tables = []
    for table in enumerate(camelot_tables):
        page_number = table.page
        dataframe = table.df
        tables.append(DataFrameTableReader(page_number, dataframe))

    return DataFrameTablesReader(pdf_path, tables)
