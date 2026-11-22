from utils.similarity import is_similar_text


def test_is_similar_trivial_scenarios():
    assert not is_similar_text("hello", "foo")
    assert is_similar_text("hello", "helloo")


def test_is_similar_normalized_scenarios():
    assert is_similar_text("HELLO", "hello")
    assert is_similar_text("    hello    ", "hello")

    assert not is_similar_text("HELLO", "hello", normalize=False)
    assert not is_similar_text("    hello    ", "hello", normalize=False)

def test_is_similar_utf_scenarios():
  assert is_similar_text("wichí", "wichi")
  assert is_similar_text("wichí", "wichi", normalize=False)

  assert is_similar_text("–", "-")
  assert is_similar_text("–", "-", normalize=False)

  assert is_similar_text("さくら", "sakura")
  assert is_similar_text("さくら", "sakura", normalize=False)