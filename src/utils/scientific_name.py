from utils.gnparser import parse_scientific_name


class scientific_name(str):
    pydantic_field_description = (
        "A taxonomical name in binomial nomenclature (e.g. Homo sapiens)"
    )

    def __new__(cls, value: str) -> "scientific_name":
        normalized = parse_scientific_name(value)
        return super().__new__(cls, normalized)
