from utils.column_type import ColumnType


class ExampleColumnType(ColumnType):
    """Column type that hints at known example values but accepts any value.

    No coercion or nullification is applied. Example values are used for
    value-based column detection and as hints in agent Pydantic models.
    """

    @classmethod
    def build(cls, *args):
        if len(args) < 1:
            raise ValueError(f"ExampleColumnType takes one or more examples")
        return cls(*args)

    def __init__(self, *examples: str):
        self._examples = frozenset(examples)
        self._examples_str = ",".join(examples)

    def coerce(self, value: str) -> str:
        return value

    def matches_value(self, value: str) -> bool:
        return value in self._examples

    def type_description(self) -> str:
        return f"Example values: {self._examples_str} (other values also valid)"

    def __repr__(self) -> str:
        return f"example:{self._examples_str}"

    def as_type(self) -> type:
        return str
