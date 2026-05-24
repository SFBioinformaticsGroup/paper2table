from typing import Protocol

from tablemerge.spacy_utils import load_spacy_model


class ValueTransformer(Protocol):
    @property
    def settings(self) -> dict: ...

    def transform(self, text: str) -> str: ...


class NullValueTransformer:
    @property
    def settings(self) -> dict:
        return {}

    def transform(self, text: str) -> str:
        return text


class ValueReverser:
    def __init__(self, language: str = "en"):
        self.language = language
        self._nlp = load_spacy_model(language)

    @property
    def settings(self) -> dict:
        return {"language": self.language}

    def count_known_words(self, text: str) -> int:
        return sum(1 for w in text.split() if self._nlp.vocab[w.lower()].has_vector)

    def transform(self, text: str) -> str:
        if not any(c.isalpha() for c in text):
            return text
        reversed_text = text[::-1]
        if self.count_known_words(reversed_text) > self.count_known_words(text):
            return reversed_text
        return text
