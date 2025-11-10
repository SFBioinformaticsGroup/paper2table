from typing import Protocol


class TableReader(Protocol):
    """
    A protocol for reading a single table
    """
    @property
    def rows(self) -> any: ...

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
    def tables(self) -> list[TableReader]: ...

    @property
    def citation(self) -> str: ...

    def to_dict(self) -> dict: ...
