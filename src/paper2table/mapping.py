

from typing import Literal
from pydantic import BaseModel


class ColumnMapping(BaseModel):
    from_column_number: int
    """
    The original column number
    """

    to_column_name: str
    """
    The desired column name
    """


class TableMapping(BaseModel):
    """
    Instructions for read_table
    about how to read a table.
    """

    title: str

    header_mode: Literal["all_pages", "first_page_only", "none"]

    first_page: int
    """
    1-based first page number where table is allocated
    """

    last_page: int
    """
    1-based last page number where table is allocated
    """

    column_mappings: list[ColumnMapping]
    """
    Mappings that go from original column number
    to desired column name
    """


class TablesMapping(BaseModel):
    tables: list[TableMapping]
    citation: str