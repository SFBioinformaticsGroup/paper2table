from typing import Iterable, Optional

from Levenshtein import ratio

# TODO make customizable
DEFAULT_SIMILARITY_THRESHOLD = 0.8


def is_similar_text(
    text: str, to: str, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> bool:
    return ratio(text, to) >= similarity_threshold


def most_similar_text(
    text: str,
    among: Iterable[str],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Optional[str]:
    candidates: list[tuple[float, str]] = []
    for to in among:
        similarity = ratio(text, to)
        if similarity >= similarity_threshold:
            candidates.append((similarity, to))

    if candidates:
        return max(candidates)[1]
