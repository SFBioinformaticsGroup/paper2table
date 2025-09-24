from typing import Protocol


class Table(Protocol):
    @property
    def rows(self) -> any: ...


class Tables(Protocol):
    @property
    def tables(self) -> list[Table]: ...

    @property
    def citation(self) -> str: ...
