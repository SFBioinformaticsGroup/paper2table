from .str import normalize_str
from tablevalidate.schema import (
    Citation,
    ValueWithAgreement,
)


def normalize_citation(citation: Citation) -> Citation:
    if citation is None:
        return None
    if isinstance(citation, str):
        return normalize_str(citation)
    return [
        ValueWithAgreement(
            value=normalize_str(v.value), agreement_level=v.agreement_level
        )
        for v in citation
    ]
