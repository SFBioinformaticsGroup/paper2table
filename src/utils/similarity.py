from typing import Iterable, Literal, Optional, Protocol

from Levenshtein import ratio
from spacy.language import Language
from unidecode import unidecode

from tablemerge.spacy_utils import load_spacy_model
from utils.str import normalize_str

# TODO make customizable
DEFAULT_SIMILARITY_THRESHOLD = 0.8


class SimilarityType(Protocol):
    def calculate(self, text: str, to: str) -> float: ...


class LexicalSimilarity:
    normalize: bool

    def __init__(self, normalize: bool = True):
        self.normalize = normalize

    def calculate(self, text: str, to: str) -> float:
        return ratio(
            text,
            to,
            processor=(
                (lambda value: unidecode(normalize_str(value)))
                if self.normalize
                else unidecode
            ),
        )


class SemanticSimilarity:
    language: Language

    def __init__(self, language: Literal["en", "es"]):
        self.language = load_spacy_model(language)

    def calculate(self, text: str, to: str) -> float:
        return self.language(text).similarity(self.language(to))


def is_similar_text(
    text: str,
    to: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    similarity_type: SimilarityType = LexicalSimilarity(),
) -> bool:
    return similarity_type.calculate(text, to) >= similarity_threshold


def most_similar_text(
    text: str,
    among: Iterable[str],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    similarity_type: SimilarityType = LexicalSimilarity(),
) -> Optional[str]:
    candidates: list[tuple[float, str]] = []
    for to in among:
        similarity = similarity_type.calculate(text, to)
        if similarity >= similarity_threshold:
            candidates.append((similarity, to))

    if candidates:
        return max(candidates)[1]
    return None
