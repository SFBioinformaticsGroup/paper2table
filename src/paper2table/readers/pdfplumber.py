import logging

import pandas as pd
import pdfplumber

from ..tables import Table, Tables
from ..tables_protocol import TablesProtocol

_logger = logging.getLogger(__name__)


def read_tables(pdf_path: str) -> TablesProtocol:
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return Tables(pdf_path, [])

    tables = []
    for page in pdf.pages:
        try:
            table_fragments = page.extract_tables()
            for table_fragment in table_fragments:
                dataframe = read_table(table_fragment)
                tables.append(Table(len(tables), page.page_number, dataframe))
        except e:
            _logger.warning(f"Error reading page {page.page_number} of {pdf_path}: {e}")

    return Tables(pdf_path, tables)


def read_table(table_fragment: list) -> pd.DataFrame:
    rows = []
    if table_fragment:
        rows += table_fragment
    dataframe = pd.DataFrame(rows)
    dataframe = dataframe.apply(
        lambda row: list(
            map(lambda v: v.replace("\n", " ") if type(v) == str else v, row)
        )
    )

    return dataframe
