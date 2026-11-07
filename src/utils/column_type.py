from abc import ABC, abstractmethod

from tablevalidate.schema import ScalarValue

_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}


class ColumnType(ABC):
    """Descriptor for a table column's type behavior.

    Instances are stored in ColumnSchema. Each instance carries coercion logic,
    value-detection hints, and Pydantic field metadata for the column.
    """

    @classmethod
    def build(cls, *args):
        if args:
            raise ValueError(f"{cls.__name__} does not take arguments")
        return cls()

    @abstractmethod
    def as_type(self) -> type: ...

    def coerce(self, value: str) -> ScalarValue | None:
        """Coerce a raw string. Return None to nullify the cell."""
        try:
            return self.as_type()(value)
        except (ValueError, TypeError):
            return None

    def __repr__(self):
        return self.as_type().__name__

    def matches_value(self, value: str) -> bool:
        """True if value is a known/valid example of this type (used for column detection)."""
        return False

    def type_description(self) -> str | None:
        """Optional description"""
        return None


class StrColumnType(ColumnType):
    def coerce(self, value: str) -> str:
        return value

    def as_type(self) -> type:
        return str


class IntColumnType(ColumnType):
    def coerce(self, value: str) -> int | str:
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return value

    def as_type(self) -> type:
        return int


class FloatColumnType(ColumnType):
    def as_type(self) -> type:
        return float


class BoolColumnType(ColumnType):
    def coerce(self, value: str) -> bool | str:
        lowered = value.lower()
        if lowered in _BOOL_TRUE:
            return True
        if lowered in _BOOL_FALSE:
            return False
        return value

    def as_type(self) -> type:
        return bool
