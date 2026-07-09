import pytest

from utils.coerce import coerce_str
from utils.gnparser import parse_scientific_name
from utils.scientific_name import scientific_name


@pytest.mark.integration
def test_parse_scientific_name_normalizes_capitalization():
    assert parse_scientific_name("homo sapiens") == "Homo sapiens"


@pytest.mark.integration
def test_parse_scientific_name_well_formed_name_unchanged():
    assert parse_scientific_name("Homo sapiens") == "Homo sapiens"


@pytest.mark.integration
def test_parse_scientific_name_unparseable_returns_original():
    assert parse_scientific_name("not a name") == "not a name"


@pytest.mark.integration
def test_scientific_name_constructor_normalizes():
    assert scientific_name("homo sapiens") == "Homo sapiens"


@pytest.mark.integration
def test_coerce_str_scientific_name_normalizes():
    assert coerce_str("homo sapiens", scientific_name) == "Homo sapiens"
