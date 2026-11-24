from typing import Callable, List, TYPE_CHECKING

from utils.column_values import normalize_column_value

if TYPE_CHECKING:
    from tablevalidate.schema import ColumnValue, ScalarValue, ValueWithAgreement


def is_na(value: "ColumnValue") -> bool:
    if value is None:
        return True

    if isinstance(value, list):
        return all(
            isinstance(v.value, str) and not normalize_column_value(v.value)
            for v in value
        )

    if isinstance(value, str):
        return not normalize_column_value(value)

    return False


def is_empty(value: "ColumnValue") -> bool:
    """True only for None, blank strings, and lists of none or blanks"""
    if value is None:
        return True

    if isinstance(value, list):
        return all(
            v.value is None or (isinstance(v.value, str) and not v.value.strip())
            for v in value
        )

    if isinstance(value, str):
        return not value.strip()

    return False


def is_convergent(value: "ColumnValue") -> bool:
    return not isinstance(value, list) or len(value) == 1


def normalize(value: "ColumnValue") -> "ColumnValue":
    from tablevalidate.schema import ValueWithAgreement

    if value is None:
        return None

    if isinstance(value, str):
        return normalize_column_value(value)

    if isinstance(value, list):
        return [
            ValueWithAgreement(
                value=(
                    normalize_column_value(v.value)
                    if isinstance(v.value, str)
                    else v.value
                ),
                agreement_level=v.agreement_level,
            )
            for v in value
        ]

    return value


def compact(value: "ColumnValue") -> "ColumnValue":
    """Merges duplicate multivalue entries, summing their agreement levels"""
    from tablevalidate.schema import ScalarValue, ValueWithAgreement

    if not isinstance(value, list):
        return value

    agreement_by_value: dict[ScalarValue, int] = {}
    for entry in value:
        if entry.value in agreement_by_value:
            agreement_by_value[entry.value] += entry.agreement_level
        else:
            agreement_by_value[entry.value] = entry.agreement_level

    return [
        ValueWithAgreement(value=entry_value, agreement_level=agreement_level)
        for entry_value, agreement_level in agreement_by_value.items()
    ]


def map_text(
    value: "ColumnValue", fn: Callable[[str], "ScalarValue"]
) -> "ColumnValue":
    """Transforms cell's string values"""
    from tablevalidate.schema import ValueWithAgreement

    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [
            ValueWithAgreement(
                value=fn(v.value) if isinstance(v.value, str) else v.value,
                agreement_level=v.agreement_level,
            )
            for v in value
        ]
    return value


def to_text(value: "ColumnValue") -> str:
    """Transforms cell's value to string"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return str(value[0].value) if value else ""
    return str(value)


def to_texts(value: "ColumnValue") -> List[str]:
    """Transforms cell's value to list of strings"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(entry.value) for entry in value]
    return [str(value)]


def to_multivalued(value: "ColumnValue") -> List["ValueWithAgreement"]:
    from tablevalidate.schema import ValueWithAgreement

    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [ValueWithAgreement(value=value, agreement_level=1)]
