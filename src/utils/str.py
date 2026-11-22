import re
import unicodedata

_NONPRINTABLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")
_CID_RE = re.compile(r"\(cid:(\d+)\)")
_DASH_VARIANTS_RE = re.compile(r"[‐‑‒–—―−]")
_GUILLEMETS_RE = re.compile(r"[«»‹›]")
_TYPOGRAPHIC_DOUBLE_QUOTES_RE = re.compile(r"[“”]")
_TYPOGRAPHIC_SINGLE_QUOTES_RE = re.compile(r"[‘’´`ʹʻʼʽ′‵]")
_VOWEL_ACUTE_RE = re.compile(r"([aeiouAEIOU])´")
_ELLIPSIS_RE = re.compile("…")
_TRAILING_DOT_RE = re.compile(r"^(.*\S{5,})\.$")


def _combine_vowel_acute(match: re.Match) -> str:
    combined = unicodedata.normalize("NFC", match.group(1) + "́")
    if len(combined) == 1:
        return combined
    return match.group(0)


def _replace_cid(match: re.Match) -> str:
    n = int(match.group(1))
    return chr(n) if 160 <= n <= 255 else ""


def normalize_str(value: str, lower=True) -> str:
    """
    Performs basic and common normalization.

    Punctuation and UTF chars are preserved.
    """
    normalized = unicodedata.normalize("NFC", value)
    normalized = _VOWEL_ACUTE_RE.sub(_combine_vowel_acute, normalized)
    normalized = _NONPRINTABLE_RE.sub("", normalized)
    normalized = _CID_RE.sub(_replace_cid, normalized)
    normalized = _DASH_VARIANTS_RE.sub("-", normalized)
    normalized = _GUILLEMETS_RE.sub("", normalized)
    normalized = _TYPOGRAPHIC_DOUBLE_QUOTES_RE.sub('"', normalized)
    normalized = normalized.replace('"', "'")
    normalized = _TYPOGRAPHIC_SINGLE_QUOTES_RE.sub("'", normalized)
    match = _TRAILING_DOT_RE.match(normalized)
    if match:
        normalized = match.group(1)
    normalized = _ELLIPSIS_RE.sub("...", normalized)

    if lower:
        normalized = normalized.lower()
    return re.sub(r"\s+", " ", normalized.strip())
