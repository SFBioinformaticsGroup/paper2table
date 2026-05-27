# pyright: reportCallIssue=false
import pytest

from tablemerge.row_transformer import NullFragmentTransformer, TableFragmentValuesReverser
from tablevalidate.schema import Row, TableFragment, ValueWithAgreement


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


def make_reverser(known: set[str]) -> TableFragmentValuesReverser:
    reverser = object.__new__(TableFragmentValuesReverser)
    reverser.language = "en"
    reverser._nlp = FakeNlp(known)  # pyright: ignore[reportAttributeAccessIssue]
    return reverser


def make_fragment(*rows: Row) -> TableFragment:
    return TableFragment(rows=list(rows), page=1)


def test_fragment_values_reverser_reverses_when_score_improves():
    reverser = make_reverser({"john", "smith", "south", "america"})
    fragment = make_fragment(Row(full_name="htims nhoj"), Row(country="acirema htuos"))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="john smith"), Row(country="south america")
    )


def test_fragment_values_reverser_keeps_when_score_does_not_improve():
    reverser = make_reverser({"john", "smith"})
    # original: row1=2, row2=0 → total=2; reversed: row1=0, row2=0 → total=0
    fragment = make_fragment(Row(full_name="john smith"), Row(country="acirema htuos"))
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_keeps_when_scores_are_tied():
    reverser = make_reverser(set())
    fragment = make_fragment(Row(full_name="eaecaipa"), Row(scientific_name="imma sujam"))
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_all_or_nothing():
    # Row 1 benefits from reversal (+2), row 2 loses (-2) → net tie → keep original
    reverser = make_reverser({"john", "smith", "north", "south"})
    fragment = make_fragment(Row(full_name="htims nhoj"), Row(country="north south"))
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_handles_none_cell_value():
    reverser = make_reverser({"john", "smith"})
    fragment = make_fragment(Row(full_name="htims nhoj", country=None))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="john smith", country=None)
    )


def test_fragment_values_reverser_reverses_list_values():
    reverser = make_reverser({"john", "smith"})
    fragment = make_fragment(
        Row(full_name=[ValueWithAgreement(value="htims nhoj", agreement_level=2)])
    )
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name=[ValueWithAgreement(value="john smith", agreement_level=2)])
    )


def test_null_fragment_transformer_keeps_fragment_unchanged():
    transformer = NullFragmentTransformer()
    fragment = make_fragment(Row(full_name="htims nhoj", country="acirema htuos"))
    assert transformer.transform_fragment(fragment) == fragment


def test_null_fragment_transformer_settings_is_empty():
    assert NullFragmentTransformer().settings == {}


def test_fragment_values_reverser_settings_contains_language():
    reverser = make_reverser(set())
    assert reverser.settings == {"language": "en"}


@pytest.mark.integration
def test_fragment_values_reverser_corrects_fully_reversed_fragment(en_spacy_model):
    reverser = TableFragmentValuesReverser("en")
    fragment = make_fragment(Row(full_name="htimS nhoJ"), Row(country="acirema htuoS"))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="John Smith"), Row(country="South america")
    )


@pytest.mark.integration
def test_fragment_values_reverser_keeps_natural_fragment(en_spacy_model):
    reverser = TableFragmentValuesReverser("en")
    fragment = make_fragment(Row(full_name="John Smith"), Row(country="South America"))
    assert reverser.transform_fragment(fragment) == fragment


@pytest.mark.integration
def test_fragment_values_reverser_keeps_fragment_with_unknown_terms(en_spacy_model):
    reverser = TableFragmentValuesReverser("en")
    fragment = make_fragment(Row(col_a="xkzqpwb vnrmt"), Row(col_b="qptnmrv bwpqzkx"))
    assert reverser.transform_fragment(fragment) == fragment
