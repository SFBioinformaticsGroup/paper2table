import logging

import camelot

from ..tables import Table, Tables
from ..tables_protocol import TablesProtocol

_logger = logging.getLogger(__name__)

def read_tables(pdf_path: str) -> TablesProtocol:
    try:
        camelot_tables = camelot.read_pdf(
            pdf_path, suppress_stdout=True, flavor="hybrid", pages="all"
        )
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return Tables(pdf_path, [])

    tables = []
    for idx, table in enumerate(camelot_tables):
        page_number = table.page
        dataframe = table.df
        tables.append(Table(idx, page_number, dataframe))

    return Tables(pdf_path, tables)
