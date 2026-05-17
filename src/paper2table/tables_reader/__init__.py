from collections.abc import Sequence
from typing import Any, Protocol


class TableReader(Protocol):
    """
    A protocol for reading a single table
    """
    @property
    def rows(self) -> Any: ...

    @property
    def page(self) -> int: ...

    def to_dict(self) -> dict: ...


class TablesReader(Protocol):
    """
    A protocol for reading tables
    from different sources.

    TablesReaders are returned by readers
    components' read_table functions
    """

    @property
    def tables(self) -> Sequence[TableReader]: ...

    @property
    def citation(self) -> str | None: ...

    def to_dict(self) -> dict: ...
