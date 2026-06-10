# pyright: reportCallIssue=false
import pytest
from tablevalidate.schema import (
    Row,
    ValueWithAgreement,
)


def test_normalize_simple_row():
    assert Row(family=" Apiaceae ", scientific_name="Ammi majus l.").normalize() == Row(
        family="apiaceae", scientific_name="ammi majus l."
    )


def test_normalize_row_with_agreement_level():
    assert Row(
        family=" Apiaceae ", scientific_name="Ammi majus L.", agreement_level_=2
    ).normalize() == Row(
        family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2
    )


def test_normalize_row_with_column_agreement_level():
    assert Row(
        family=[
            ValueWithAgreement(value=" Apiaceae ", agreement_level=1),
            ValueWithAgreement(value="Amni ", agreement_level=1),
        ],
        scientific_name=[ValueWithAgreement(value="Ammi majus L.", agreement_level=2)],
    ).normalize() == Row(
        family=[
            ValueWithAgreement(value="apiaceae", agreement_level=1),
            ValueWithAgreement(value="amni", agreement_level=1),
        ],
        scientific_name=[ValueWithAgreement(value="ammi majus l.", agreement_level=2)],
    )


def test_normalize_row_with_mixed_values():
    assert Row(
        family=[ValueWithAgreement(value=" Apiaceae ", agreement_level=2)],
        scientific_name="Ammi majus L.",
    ).normalize() == Row(
        family=[ValueWithAgreement(value="apiaceae", agreement_level=2)],
        scientific_name="ammi majus l.",
    )


def test_normalize_row_preserves_sources():
    uuids = ["uuid-a", "uuid-b"]
    assert Row(
        family=" Apiaceae ", scientific_name="Ammi majus L.", sources_=uuids
    ).normalize() == Row(
        family="apiaceae", scientific_name="ammi majus l.", sources_=uuids
    )


def test_normalize_row_preserves_none_sources():
    assert Row(
        family=" Apiaceae ", scientific_name="Ammi majus L.", sources_=None
    ).normalize() == Row(
        family="apiaceae", scientific_name="ammi majus l.", sources_=None
    )
