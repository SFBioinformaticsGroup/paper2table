# pyright: reportCallIssue=false
import pytest

from tablemerge.value_transformer import NullValueTransformer, ValueReverser


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


def make_reverser(known: set[str]) -> ValueReverser:
    reverser = object.__new__(ValueReverser)
    reverser.language = "en"
    reverser._nlp = FakeNlp(known)  # pyright: ignore[reportAttributeAccessIssue]
    return reverser


def test_value_reverser_reverses_when_reversed_has_more_known_words():
    reverser = make_reverser({"john", "smith"})
    assert reverser.transform("htims nhoj") == "john smith"


def test_value_reverser_keeps_original_when_scores_are_tied():
    reverser = make_reverser({"rats", "star"})
    assert reverser.transform("rats") == "rats"


def test_value_reverser_keeps_original_when_scores_are_zero():
    reverser = make_reverser(set())
    assert reverser.transform("eaecaipa") == "eaecaipa"


def test_value_reverser_keeps_original_when_no_alphabetic_chars():
    reverser = make_reverser({"123", "321"})
    assert reverser.transform("123-456") == "123-456"


def test_null_value_transformer_keeps_text_unchanged():
    transformer = NullValueTransformer()
    assert transformer.transform("htims nhoj") == "htims nhoj"


def test_null_value_transformer_settings_is_empty():
    assert NullValueTransformer().settings == {}


def test_value_reverser_settings_contains_language():
    reverser = make_reverser(set())
    assert reverser.settings == {"language": "en"}


@pytest.mark.integration
def test_value_reverser_corrects_reversed_person_name(en_spacy_model):
    reverser = ValueReverser("en")
    assert reverser.transform("htimS nhoJ") == "John Smith"


@pytest.mark.integration
def test_value_reverser_keeps_valid_person_name(en_spacy_model):
    reverser = ValueReverser("en")
    assert reverser.transform("John Smith") == "John Smith"


@pytest.mark.integration
def test_value_reverser_keeps_unknown_latin_name(en_spacy_model):
    reverser = ValueReverser("en")
    assert reverser.transform("eaecaipA") == "eaecaipA"


@pytest.mark.integration
def test_value_reverser_keeps_code_unchanged(en_spacy_model):
    reverser = ValueReverser("en")
    assert reverser.transform("ABC-123") == "ABC-123"
