import pytest

from utils.gnparser import parse_scientific_name


@pytest.mark.integration
def test_scientific_name_simple_binomen():
    assert parse_scientific_name("homo sapiens") == "Homo sapiens"
    assert parse_scientific_name("Homo sapiens") == "Homo sapiens"


@pytest.mark.integration
def test_scientific_name_unparseable_returns_original():
    assert parse_scientific_name("not a name") == "not a name"


@pytest.mark.integration
def test_scientific_name_binomen_with_tail():
    assert (
        parse_scientific_name("Acantholippia seriphioides (a. gray) mold.")
        == "Acantholippia seriphioides"
    )
    assert (
        parse_scientific_name("acantholippia seriphioides (a. gray) mold.")
        == "Acantholippia seriphioides"
    )
    assert parse_scientific_name("apium australe pet. thouars") == "Apium australe"


@pytest.mark.integration
def test_scientific_name_binomen_with_author():
    assert (
        parse_scientific_name("Acantholippia seriphioides (A. Gray) Mold.")
        == "Acantholippia seriphioides"
    )
    assert parse_scientific_name("Apium australe Pet. Thouars") == "Apium australe"


@pytest.mark.integration
def test_scientific_name_approximation():
    assert parse_scientific_name("acaena sp.") == "Acaena"


@pytest.mark.integration
def test_scientific_name_comma_separated():
    assert (
        parse_scientific_name("homo sapiens, pan troglodytes")
        == "Homo sapiens, Pan troglodytes"
    )


@pytest.mark.integration
def test_scientific_name_slash_separated():
    assert (
        parse_scientific_name("homo sapiens / pan troglodytes")
        == "Homo sapiens, Pan troglodytes"
    )


@pytest.mark.integration
def test_scientific_name_comma_separated_strips_authors():
    assert (
        parse_scientific_name(
            "Acantholippia seriphioides (A. Gray) Mold., Apium australe Pet. Thouars"
        )
        == "Acantholippia seriphioides, Apium australe"
    )


@pytest.mark.integration
def test_scientific_name_comma_separated_with_unparseable_part():
    assert (
        parse_scientific_name("homo sapiens, not a name") == "Homo sapiens, not a name"
    )
