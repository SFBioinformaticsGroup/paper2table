
from typing import Literal, Optional
from pydantic import BaseModel


class ColumnMapping(BaseModel):
    from_column_name: Optional[str] = None
    """
    Expected column header text. When provided, the extraction algorithm verifies
    that the header cell at `from_column_number` matches this value. If the cell is
    only a prefix of this value, adjacent column headers are concatenated (without
    spaces) until a full match is found or 5 attempts are exhausted. All physical
    columns that participated in the match are merged into one: their data cells
    are space-joined in every data row.
    """

    from_column_number: int
    """
    The original column number (0-based). Used as the starting point when
    `from_column_name` is set, or as the sole column selector otherwise.
    """

    to_column_name: str
    """
    The desired column name in the output.
    """


class TableRowMappings(BaseModel):
    header_row: Optional[int] = None
    """
    0-based index of the row containing column names within the raw extracted rows
    (after content-based title removal). Used for `from_column_name` matching and
    physical-column accumulation. When absent, no column-name row is assumed.
    """

    first_data_row: Optional[int] = None
    """
    0-based index of the first data row within the raw extracted rows (after
    content-based title removal). Defaults to `header_row + 1` when `header_row`
    is set, or `0` otherwise.
    """


class TableMapping(BaseModel):
    title: str
    """
    Human-readable table title used for display and as a row-removal filter.
    """

    footer: Optional[str] = None
    """
    Human-readable table footer used for display and as a row-removal filter.
    """

    page_footer: Optional[str] = None
    """
    Human-readable page footer used for display and as a row-removal filter.
    """

    header_mode: Literal["all_pages", "first_page_only", "none"]

    first_page: int
    """
    1-based first page number where the table is located.
    """

    last_page: int
    """
    1-based last page number where the table is located.
    """

    row_mappings: Optional[TableRowMappings] = None
    """
    Explicit row-index overrides for header and data boundaries within each
    extracted page. When absent, `header_mode` governs header detection.
    """

    column_mappings: list[ColumnMapping]
    """
    Ordered list of column selections and renames applied after physical-column
    merging (see `ColumnMapping.from_column_name`).
    """


class TablesMappingMetadata(BaseModel):
    model: str
    date: str


class TablesMapping(BaseModel):
    tables: list[TableMapping]
    citation: str
    metadata: Optional[TablesMappingMetadata] = None
