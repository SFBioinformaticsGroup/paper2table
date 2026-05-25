# pyright: reportCallIssue=false
import pytest

from tablemerge.row_transformer import NullRowTransformer, RowReverser
from tablevalidate.schema import Row, ValueWithAgreement


class FakeVocab:
    def __init__(self, known: set[str]):
        self._known = known

    def __getitem__(self, word: str):
        return type("Lex", (), {"has_vector": word in self._known})()


class FakeNlp:
    def __init__(self, known: set[str]):
        self.vocab = FakeVocab(known)


@pytest.fixture(scope="session")
def en_spacy_model():
    import spacy

    try:
        spacy.load("en_core_web_md")
    except OSError:
        spacy.cli.download(  # pyright: ignore[reportAttributeAccessIssue]
            "en_core_web_md"
        )


def make_reverser(known: set[str]) -> RowReverser:
    reverser = object.__new__(RowReverser)
    reverser.language = "en"
    reverser._nlp = FakeNlp(known)  # pyright: ignore[reportAttributeAccessIssue]
    return reverser


def test_row_reverser_reverses_row_when_total_score_improves():
    reverser = make_reverser({"john", "smith", "south", "america"})
    row = Row(full_name="htims nhoj", country="acirema htuos")
    assert reverser.transform(row) == Row(full_name="john smith", country="south america")


def test_row_reverser_keeps_row_when_reversal_lowers_total_score():
    # "john" and "smith" are known; reversing "john smith" → "htims nhoj" would score 0
    reverser = make_reverser({"john", "smith"})
    row = Row(full_name="john smith", country="acirema htuos")
    # original score: full_name=2, country=0 → total=2
    # reversed score: full_name=0, country=0 → total=0  (htims nhoj → john smith loses 2, htuos acirema stays 0)
    # Wait: reversed of "john smith" = "htims nhoj", reversed of "acirema htuos" = "south america"
    # but "south" and "america" are NOT in known set → reversed country score=0
    # reversed total = 0+0 = 0 < 2 → keep original
    assert reverser.transform(row) == Row(full_name="john smith", country="acirema htuos")


def test_row_reverser_keeps_row_when_total_score_does_not_improve():
    # original: "john"=1, "smith"=1 → total=2
    # reversed: "htims nhoj" → "htims"=0, "nhoj"=0 → total=0; "acirema htuos" → 0
    # 0 < 2 → keep original
    reverser = make_reverser({"john", "smith"})
    row = Row(full_name="john smith", country="acirema htuos")
    assert reverser.transform(row) == Row(full_name="john smith", country="acirema htuos")


def test_row_reverser_handles_none_cell_value():
    reverser = make_reverser({"john", "smith"})
    row = Row(full_name="htims nhoj", country=None)
    assert reverser.transform(row) == Row(full_name="john smith", country=None)


def test_row_reverser_keeps_row_when_scores_are_tied():
    reverser = make_reverser(set())
    row = Row(full_name="eaecaipa", scientific_name="imma sujam")
    assert reverser.transform(row) == Row(full_name="eaecaipa", scientific_name="imma sujam")


def test_row_reverser_reverses_list_values():
    reverser = make_reverser({"john", "smith"})
    row = Row(
        full_name=[ValueWithAgreement(value="htims nhoj", agreement_level=2)]
    )
    result = reverser.transform(row)
    assert result == Row(
        full_name=[ValueWithAgreement(value="john smith", agreement_level=2)]
    )


def test_row_reverser_skips_row_with_multiple_sources():
    reverser = make_reverser({"john", "smith"})
    row = Row(full_name="htims nhoj", sources_=["uuid-a", "uuid-b"])
    assert reverser.transform(row) == Row(full_name="htims nhoj", sources_=["uuid-a", "uuid-b"])


def test_null_row_transformer_keeps_row_unchanged():
    transformer = NullRowTransformer()
    row = Row(full_name="htims nhoj", country="acirema htuos")
    assert transformer.transform(row) == row


def test_null_row_transformer_settings_is_empty():
    assert NullRowTransformer().settings == {}


def test_row_reverser_settings_contains_language():
    reverser = make_reverser(set())
    assert reverser.settings == {"language": "en"}


@pytest.mark.integration
def test_row_reverser_corrects_fully_reversed_row(en_spacy_model):
    reverser = RowReverser("en")
    row = Row(full_name="htimS nhoJ", country="acirema htuoS")
    result = reverser.transform(row)
    assert result == Row(full_name="John Smith", country="South america")


@pytest.mark.integration
def test_row_reverser_keeps_natural_row(en_spacy_model):
    reverser = RowReverser("en")
    row = Row(full_name="John Smith", country="South America")
    assert reverser.transform(row) == Row(full_name="John Smith", country="South America")


@pytest.mark.integration
def test_row_reverser_keeps_row_with_unknown_terms(en_spacy_model):
    reverser = RowReverser("en")
    row = Row(col_a="xkzqpwb vnrmt", col_b="qptnmrv bwpqzkx")
    assert reverser.transform(row) == Row(col_a="xkzqpwb vnrmt", col_b="qptnmrv bwpqzkx")
