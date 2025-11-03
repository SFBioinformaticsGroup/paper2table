import pytest
from tablemerge.merge import normalize_row
from tablevalidate.schema import (
    Row,
    ValueWithAgreement,
)


def test_normalize_simple_row():
    assert normalize_row(
        Row(family=" Apiaceae ", scientific_name="Ammi majus L.")
    ) == Row(family="apiaceae", scientific_name="ammi majus l.")


def test_normalize_row_with_agreement_level():
    assert normalize_row(
        Row(family=" Apiaceae ", scientific_name="Ammi majus L.", agreement_level_=2)
    ) == Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2)


def test_normalize_row_with_column_agreement_level():
    assert normalize_row(
        Row(
            family=[
                ValueWithAgreement(value=" Apiaceae ", agreement_level=1),
                ValueWithAgreement(value="Amni ", agreement_level=1),
            ],
            scientific_name=[
                ValueWithAgreement(value="Ammi majus L.", agreement_level=2)
            ],
        )
    ) == Row(
        family=[
            ValueWithAgreement(value="apiaceae", agreement_level=1),
            ValueWithAgreement(value="amni", agreement_level=1),
        ],
        scientific_name=[ValueWithAgreement(value="ammi majus l.", agreement_level=2)],
    )


def test_normalize_row_with_mixed_values():
    assert normalize_row(
        Row(
            family=[ValueWithAgreement(value=" Apiaceae ", agreement_level=2)],
            scientific_name="Ammi majus L.",
        ),
    ) == Row(
        family=[ValueWithAgreement(value="apiaceae", agreement_level=2)],
        scientific_name="ammi majus l.",
    )
