import pytest

from utils.similarity import (
    LexicalSimilarity,
    SemanticSimilarity,
    is_similar_text,
    most_similar_text,
)


@pytest.fixture(scope="session")
def es_spacy_model():
    import spacy

    try:
        spacy.load("es_core_news_md")
    except OSError:
        spacy.cli.download(  # pyright: ignore[reportAttributeAccessIssue]
            "es_core_news_md"
        )


def test_is_similar_trivial_scenarios():
    assert not is_similar_text("hello", "foo")
    assert is_similar_text("hello", "helloo")


def test_is_similar_normalized_scenarios():
    assert is_similar_text("HELLO", "hello")
    assert is_similar_text("    hello    ", "hello")

    assert not is_similar_text(
        "HELLO", "hello", similarity_type=LexicalSimilarity(normalize=False)
    )
    assert not is_similar_text(
        "    hello    ", "hello", similarity_type=LexicalSimilarity(normalize=False)
    )


def test_is_similar_utf_scenarios():
    assert is_similar_text("wichí", "wichi")
    assert is_similar_text(
        "wichí", "wichi", similarity_type=LexicalSimilarity(normalize=False)
    )

    assert is_similar_text("–", "-")
    assert is_similar_text("–", "-", similarity_type=LexicalSimilarity(normalize=False))

    assert is_similar_text("さくら", "sakura")
    assert is_similar_text(
        "さくら", "sakura", similarity_type=LexicalSimilarity(normalize=False)
    )


def test_lexical_similarity_calculate_returns_ratio():
    assert LexicalSimilarity().calculate("hello", "hello") == 1.0
    assert LexicalSimilarity().calculate("hello", "world") < 0.5


def test_lexical_similarity_normalize_true_folds_case_and_whitespace():
    similarity = LexicalSimilarity()
    assert similarity.calculate("HELLO", "hello") == 1.0
    assert similarity.calculate("    hello    ", "hello") == 1.0


def test_lexical_similarity_normalize_false_preserves_case_and_whitespace():
    similarity = LexicalSimilarity(normalize=False)
    assert similarity.calculate("HELLO", "hello") < 1.0
    assert similarity.calculate("    hello    ", "hello") < 1.0


def test_most_similar_text_returns_best_candidate_above_threshold():
    assert most_similar_text("hello", ["helloo", "world", "foo"]) == "helloo"


def test_most_similar_text_returns_none_when_no_candidate_passes_threshold():
    assert most_similar_text("hello", ["world", "foo", "bar"]) is None


def test_most_similar_text_returns_none_for_empty_candidates():
    assert most_similar_text("hello", []) is None


def test_most_similar_text_picks_highest_ratio_among_candidates():
    assert most_similar_text("hello", ["hellooo", "helloo"]) == "helloo"


def test_most_similar_text_respects_custom_similarity_type():
    assert (
        most_similar_text(
            "HELLO",
            ["hello"],
            similarity_type=LexicalSimilarity(normalize=False),
        )
        is None
    )
    assert most_similar_text("HELLO", ["hello"]) == "hello"


@pytest.mark.integration
def test_semantic_similarity_identical_terms(es_spacy_model):
    assert SemanticSimilarity("es").calculate("tallo", "tallo") == pytest.approx(1.0)


@pytest.mark.integration
def test_semantic_similarity_ranks_related_plant_parts_above_unrelated(es_spacy_model):
    semantic = SemanticSimilarity("es")
    assert semantic.calculate("tallo", "tallos") > semantic.calculate("tallo", "raices")
    assert semantic.calculate("tallo", "tallos verdes") > semantic.calculate(
        "tallo", "raices"
    )


@pytest.mark.integration
def test_most_similar_text_with_semantic_similarity(es_spacy_model):
    assert (
        most_similar_text(
            "tallos verdes",
            ["tallo", "hoja", "raíz"],
            similarity_type=SemanticSimilarity("es"),
        )
        == "tallos"
    )
