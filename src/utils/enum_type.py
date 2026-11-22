from utils.column_type import ColumnType
from utils.similarity import most_similar_text

class EnumColumnType(ColumnType):
    """Column type that accepts only a finite set of known values.

    Values outside the set are nullified during coercion.
    All values contribute to value-based column detection.
    """

    @classmethod
    def build(cls, *args):
        if len(args) < 1:
            raise ValueError(f"EnumColumnType takes one or more values")
        return cls(*args)

    def __init__(self, *values: str):
        self._values = frozenset(values)
        self._values_str = ",".join(values)

    def coerce(self, value: str) -> str | None:
        """Coerces to the most similar value, if there is one"""
        candidate = most_similar_text(value, self._values)
        return candidate if candidate else None

    def matches_value(self, value: str) -> bool:
        return value in self._values

    def type_description(self) -> str:
        return f"Must be one of: {self._values_str}"

    def __str__(self) -> str:
        return f"enum:{self._values_str}"

    def as_type(self) -> type:
        return str
