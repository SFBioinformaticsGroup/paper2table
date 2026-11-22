import re
import unicodedata

NONPRINTABLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")
CID_RE = re.compile(r"\(cid:(\d+)\)")


def _replace_cid(match: re.Match) -> str:
    n = int(match.group(1))
    return chr(n) if 160 <= n <= 255 else ""


def normalize_str(value: str, lower=True) -> str:
    """
    Performs basic and common normalization.

    Punctuation and UTF chars are preserved.
    """
    normalized = unicodedata.normalize("NFC", value)
    normalized = NONPRINTABLE_RE.sub("", normalized)
    normalized = CID_RE.sub(_replace_cid, normalized)
    normalized = re.sub(r"[‐‑‒–—―−]", "-", normalized)
    if lower:
        normalized = normalized.lower()
    return re.sub(r"\s+", " ", normalized.strip())
