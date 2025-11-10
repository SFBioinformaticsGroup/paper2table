from typing import Protocol


class TableProtocol(Protocol):
    @property
    def rows(self) -> any: ...

    @property
    def page(self) -> int: ...

    def to_dict(self) -> dict: ...

class TablesProtocol(Protocol):
    @property
    def tables(self) -> list[TableProtocol]: ...

    @property
    def citation(self) -> str: ...

    def to_dict(self) -> dict: ...
