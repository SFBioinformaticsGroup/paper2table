import pytest

from utils.scientific_name_type import ScientificNameColumnType


@pytest.mark.integration
def test_coerce_value_scientific_name_normalizes():
    assert (
        ScientificNameColumnType().coerce("maytenus ilicifolia mart.")
        == "Maytenus ilicifolia"
    )
