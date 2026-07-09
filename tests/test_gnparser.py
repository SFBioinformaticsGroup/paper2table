import pytest

from utils.scientific_name import scientific_name

@pytest.mark.integration
def test_scientific_name_simple_binomen():
    assert scientific_name("homo sapiens") == "Homo sapiens"
    assert scientific_name("Homo sapiens") == "Homo sapiens"

@pytest.mark.integration
def test_scientific_name_unparseable_returns_original():
    assert scientific_name("not a name") == "not a name"

@pytest.mark.integration
def test_scientific_name_binomen_with_tail():
    assert scientific_name("Acantholippia seriphioides (a. gray) mold.") == "Acantholippia seriphioides"
    assert scientific_name("acantholippia seriphioides (a. gray) mold.") == "Acantholippia seriphioides"
    assert scientific_name("apium australe pet. thouars") == "Apium australe"

@pytest.mark.integration
def test_scientific_name_binomen_with_author():
    assert scientific_name("Acantholippia seriphioides (A. Gray) Mold.") == "Acantholippia seriphioides"
    assert scientific_name("Apium australe Pet. Thouars") == "Apium australe"

@pytest.mark.integration
def test_scientific_name_approximation():
    assert scientific_name("acaena sp.") == "Acaena"
