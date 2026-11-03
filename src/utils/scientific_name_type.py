from utils.column_type import ColumnType
from utils.gnparser import parse_scientific_name


class ScientificNameColumnType(ColumnType):
    def type_description(self) -> str:
        return "A taxonomical name in binomial nomenclature (e.g. Homo sapiens)"

    def coerce(self, value: str):
        return parse_scientific_name(value)

    def __repr__(self):
        return "scientific_name"

    def as_type(self):
        return str
