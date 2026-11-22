from typing import Iterable, Optional

from Levenshtein import ratio
from unidecode import unidecode

from utils.str import normalize_str

# TODO make customizable
DEFAULT_SIMILARITY_THRESHOLD = 0.8


def calculate_similarity(text: str, to: str, normalize: bool = True):
    return ratio(
        text,
        to,
        processor=(
            (lambda str: unidecode(normalize_str(str)).lower()) if normalize else None
        ),
    )


def is_similar_text(
    text: str,
    to: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    normalize: bool = True,
) -> bool:
    return calculate_similarity(text, to, normalize) >= similarity_threshold


def most_similar_text(
    text: str,
    among: Iterable[str],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    normalize: bool = True,
) -> Optional[str]:
    candidates: list[tuple[float, str]] = []
    for to in among:
        similarity = calculate_similarity(text, to, normalize)
        if similarity >= similarity_threshold:
            candidates.append((similarity, to))

    if candidates:
        return max(candidates)[1]
