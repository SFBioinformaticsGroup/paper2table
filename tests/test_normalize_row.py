# pyright: reportCallIssue=false
import pytest
from tablevalidate.schema import (
    Row,
    ValueWithAgreement,
)
from utils.str import normalize_str


def test_normalize_simple_row():
    assert Row(family=" Apiaceae ", scientific_name="Ammi majus l.").normalize() == Row(
        agreement_level_=1, family="apiaceae", scientific_name="ammi majus l."
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
        agreement_level_=1,
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
        agreement_level_=1,
        family=[ValueWithAgreement(value="apiaceae", agreement_level=2)],
        scientific_name="ammi majus l.",
    )


def test_normalize_row_preserves_sources():
    sources = ["uuid-a", "uuid-b"]
    assert Row(
        family=" Apiaceae ", scientific_name="Ammi majus L.", sources_=sources
    ).normalize() == Row(
        agreement_level_=1,
        family="apiaceae",
        scientific_name="ammi majus l.",
        sources_=sources,
    )


def test_normalize_row_preserves_none_sources():
    assert Row(
        family=" Apiaceae ", scientific_name="Ammi majus L.", sources_=None
    ).normalize() == Row(
        agreement_level_=1,
        family="apiaceae",
        scientific_name="ammi majus l.",
        sources_=None,
    )

def test_normalize_row_with_decomposed_accent_in_str_value_normalize_str():
    # "lant" + e (U+0065) + combining acute (U+0301) + "n" — NFD/decomposed form
    decomposed = "lantén"
    # "lant" + é (U+00E9) + "n" — NFC/precomposed form
    precomposed = "lantén"
    assert normalize_str(decomposed) ==precomposed


def test_normalize_row_with_decomposed_accent_in_str_value():
    # "lant" + e (U+0065) + combining acute (U+0301) + "n" — NFD/decomposed form
    decomposed = "lantén"
    # "lant" + é (U+00E9) + "n" — NFC/precomposed form
    precomposed = "lantén"
    assert Row(genus=decomposed).normalize() == Row(
        agreement_level_=1, genus=precomposed
    )


def test_normalize_row_with_decomposed_accent_in_agreement_value():
    decomposed = "lantén"
    precomposed = "lantén"
    assert Row(
        genus=[ValueWithAgreement(value=decomposed, agreement_level=1)]
    ).normalize() == Row(
        agreement_level_=1,
        genus=[ValueWithAgreement(value=precomposed, agreement_level=1)],
    )


def test_normalize_row_converts_dash_variants():
    row = Row(period="2010–2020", range="5—7")
    assert row.normalize() == Row(agreement_level_=1, period="2010-2020", range="5-7")


def test_normalize_row_removes_guillemets():
    row = Row(species="«Homo sapiens»", note="‹present›")
    assert row.normalize() == Row(
        agreement_level_=1, species="homo sapiens", note="present"
    )


def test_normalize_row_converts_typographic_double_quotes_to_single():
    row = Row(value="“positive”")
    assert row.normalize() == Row(agreement_level_=1, value="'positive'")


def test_normalize_row_converts_straight_double_quotes_to_single():
    row = Row(value='"yes"')
    assert row.normalize() == Row(agreement_level_=1, value="'yes'")


def test_normalize_row_normalizes_typographic_apostrophe():
    row = Row(note="don’t", opening="L’Hopital")
    assert row.normalize() == Row(agreement_level_=1, note="don't", opening="l'hopital")


def test_normalize_row_combines_acute_with_vowel():
    row = Row(city="Mo´nica", note="u´ltimo")
    assert row.normalize() == Row(agreement_level_=1, city="mónica", note="último")


def test_normalize_row_acute_after_non_vowel_becomes_apostrophe():
    row = Row(note="don´t", opening="L´Hopital")
    assert row.normalize() == Row(agreement_level_=1, note="don't", opening="l'hopital")


def test_normalize_row_normalizes_grave_accent_apostrophe():
    row = Row(note="don`t", opening="L`Hopital")
    assert row.normalize() == Row(agreement_level_=1, note="don't", opening="l'hopital")


def test_normalize_row_normalizes_prime_apostrophe():
    row = Row(note="don′t", opening="L′Hopital")
    assert row.normalize() == Row(agreement_level_=1, note="don't", opening="l'hopital")


def test_normalize_row_normalizes_modifier_letter_apostrophe():
    row = Row(note="donʼt", opening="Lʻopital")
    assert row.normalize() == Row(agreement_level_=1, note="don't", opening="l'opital")


def test_normalize_row_converts_ellipsis():
    row = Row(note="see below…")
    assert row.normalize() == Row(agreement_level_=1, note="see below...")


def test_normalize_row_removes_trailing_dot_after_long_word():
    row = Row(species="Homo sapiens.", location="North America.")
    assert row.normalize() == Row(
        agreement_level_=1, species="homo sapiens", location="north america"
    )


def test_normalize_row_keeps_trailing_dot_after_short_word():
    row = Row(citation="et al.", figure="Fig.", taxon="spp.", rank="sp.")
    assert row.normalize() == (
        Row(
            agreement_level_=1,
            citation="et al.",
            figure="fig.",
            taxon="spp.",
            rank="sp.",
        )
    )


def test_normalize_row_handles_none_value():
    row = Row(species="Homo sapiens.", note=None)
    assert row.normalize() == Row(agreement_level_=1, species="homo sapiens", note=None)


def test_normalize_row_transforms_list_values():
    row = Row(
        species=[
            ValueWithAgreement(value="Homo sapiens.", agreement_level=2),
            ValueWithAgreement(value="“positive”", agreement_level=1),
        ]
    )
    assert row.normalize() == (
        Row(
            agreement_level_=1,
            species=[
                ValueWithAgreement(value="homo sapiens", agreement_level=2),
                ValueWithAgreement(value="'positive'", agreement_level=1),
            ],
        )
    )


def test_normalize_row_preserves_row_meta_columns():
    row = Row(species="Homo sapiens.", agreement_level_=3, sources_=["s1"], row_=5)
    assert row.normalize() == (
        Row(species="homo sapiens", agreement_level_=3, sources_=["s1"], row_=5)
    )
