import re

NONPRINTABLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")
CID_RE = re.compile(r"\(cid:(\d+)\)")


def _replace_cid(match: re.Match) -> str:
    n = int(match.group(1))
    return chr(n) if 160 <= n <= 255 else ""

def normalize_str(value: str) -> str:
    value = NONPRINTABLE_RE.sub("", value)
    value = CID_RE.sub(_replace_cid, value)
    normalized = re.sub(r"[‐‑‒–—―−]", "-", value)
    return re.sub(r"\s+", " ", normalized.strip())
