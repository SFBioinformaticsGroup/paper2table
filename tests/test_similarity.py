from utils.similarity import is_similar_text


def test_is_similar_trivial_scenarios():
    assert not is_similar_text("hello", "foo")
    assert is_similar_text("hello", "helloo")


def test_is_similar_normalized_scenarios():
    assert is_similar_text("raíz", "raiz")

    assert is_similar_text("HELLO", "hello")
    assert is_similar_text("    hello    ", "hello")
    assert is_similar_text("–", "-")

    assert not is_similar_text("HELLO", "hello", normalize=False)
    assert not is_similar_text("    hello    ", "hello", normalize=False)
    assert not is_similar_text("–", "-", normalize=False)