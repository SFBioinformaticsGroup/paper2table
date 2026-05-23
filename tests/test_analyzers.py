# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import pytest

from tablemerge.analyzers import AliasAnalyzer, JaccardAnalyzer, SemanticAnalyzer
from tablemerge.columns_aligner import ColumnAligner
from tablevalidate.schema import Row, TableFragment
from test_columns_aligner import FOUR_COLUMNS_MAPPING, SPECIES, SPECIES_WITH_EDITS


@pytest.fixture(scope="session")
def en_spacy_model():
    import spacy
    try:
        spacy.load("en_core_web_md")
    except OSError:
        spacy.cli.download("en_core_web_md")


@pytest.fixture(scope="session")
def es_spacy_model():
    import spacy
    try:
        spacy.load("es_core_news_md")
    except OSError:
        spacy.cli.download("es_core_news_md")


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_jaccard_numeric_to_semantic():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    result = JaccardAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "family"}


def test_jaccard_both_semantic_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = JaccardAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_no_overlap_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"0": "red"})])
    result = JaccardAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_threshold_respected():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert JaccardAnalyzer(threshold=0.5).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    ) == {"0": "family"}
    assert (
        JaccardAnalyzer(threshold=0.6).build_mapping(
            left.get_column_names(), right.get_column_names(), left.rows, right.rows
        )
        == {}
    )


def test_alias_applies_known_alias():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"familia": "family"}


def test_alias_ignores_unknown_cols():
    left = wrap([Row(**{"genus": "Ammi"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_alias_maps_both_left_and_right():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"especie": "Ammi majus"})])
    result = AliasAnalyzer({"familia": "family", "especie": "species"}).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"familia": "family", "especie": "species"}


def test_alias_deduplicates_when_col_in_both_sides():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"familia": "Rosaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"familia": "family"}


def test_semantic_returns_empty_when_both_numeric():
    left = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    right = wrap([Row(**{"1": "Apiaceae"}), Row(**{"1": "Rosaceae"})])
    result = SemanticAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_semantic_returns_empty_when_both_semantic():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = SemanticAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_semantic_returns_empty_when_numeric_rows_are_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([])
    result = SemanticAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_semantic_returns_empty_both_numeric_species_data():
    rows = [
        Row(**{"0": scientific_name, "1": area, "2": family, "3": vernacular_name})
        for scientific_name, area, family, vernacular_name in SPECIES
    ]
    left = wrap(rows)
    right = wrap(rows)
    result = SemanticAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_semantic_returns_empty_both_semantic_species_data():
    rows = [
        Row(
            scientific_name=scientific_name,
            area=area,
            family=family,
            vernacular_name=vernacular_name,
        )
        for scientific_name, area, family, vernacular_name in SPECIES
    ]
    left = wrap(rows)
    right = wrap(rows)
    result = SemanticAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


@pytest.mark.integration
def test_semantic_maps_color_values_to_color_column(en_spacy_model):
    left = wrap(
        [
            Row(**{"color": color_value})
            for color_value in ["red", "blue", "green", "yellow"]
        ]
    )
    right = wrap(
        [
            Row(**{"0": color_value})
            for color_value in ["orange", "purple", "cyan", "brown"]
        ]
    )
    result = SemanticAnalyzer(threshold=0.3).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "color"}


@pytest.mark.integration
def test_semantic_does_not_map_below_threshold(en_spacy_model):
    left = wrap(
        [
            Row(**{"color": color_value})
            for color_value in ["red", "blue", "green", "yellow"]
        ]
    )
    right = wrap(
        [
            Row(**{"0": color_value})
            for color_value in ["orange", "purple", "cyan", "brown"]
        ]
    )
    result = SemanticAnalyzer(threshold=0.99).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


@pytest.mark.integration
def test_semantic_maps_color_values_to_color_column_in_spanish(es_spacy_model):
    left = wrap(
        [
            Row(**{"color": color_value})
            for color_value in ["rojo", "azul", "verde", "amarillo"]
        ]
    )
    right = wrap(
        [
            Row(**{"0": color_value})
            for color_value in ["naranja", "morado", "rosa", "blanco"]
        ]
    )
    result = SemanticAnalyzer(threshold=0.3, language="es").build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "color"}


@pytest.mark.integration
def test_semantic_does_not_map_below_threshold_in_spanish(es_spacy_model):
    left = wrap(
        [
            Row(**{"color": color_value})
            for color_value in ["rojo", "azul", "verde", "amarillo"]
        ]
    )
    right = wrap(
        [
            Row(**{"0": color_value})
            for color_value in ["naranja", "morado", "rosa", "blanco"]
        ]
    )
    result = SemanticAnalyzer(threshold=0.99, language="es").build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


@pytest.mark.integration
def test_semantic_chain_does_not_disrupt_jaccard_on_species_exact(en_spacy_model):
    left = wrap(
        [
            Row(
                scientific_name=scientific_name,
                area=area,
                family=family,
                vernacular_name=vernacular_name,
            )
            for scientific_name, area, family, vernacular_name in SPECIES
        ]
    )
    right = wrap(
        [
            Row(**{"0": scientific_name, "1": area, "2": family, "3": vernacular_name})
            for scientific_name, area, family, vernacular_name in SPECIES
        ]
    )
    aligner = ColumnAligner(
        left, right, analyzers=[JaccardAnalyzer(0.5), SemanticAnalyzer(0.3)]
    )
    assert aligner.mapping == FOUR_COLUMNS_MAPPING


@pytest.mark.integration
def test_semantic_chain_species_edits_preserves_jaccard_mappings(en_spacy_model):
    left = wrap(
        [
            Row(
                scientific_name=scientific_name,
                area=area,
                family=family,
                vernacular_name=vernacular_name,
            )
            for scientific_name, area, family, vernacular_name in SPECIES
        ]
    )
    right = wrap(
        [
            Row(**{"0": scientific_name, "1": area, "2": family, "3": vernacular_name})
            for scientific_name, area, family, vernacular_name in SPECIES_WITH_EDITS
        ]
    )
    jaccard_mapping = ColumnAligner(
        left, right, analyzers=[JaccardAnalyzer(0.6)]
    ).mapping
    assert jaccard_mapping == {"1": "area", "2": "family"}

    chain_mapping = ColumnAligner(
        left, right, analyzers=[JaccardAnalyzer(0.6), SemanticAnalyzer(0.1)]
    ).mapping
    assert chain_mapping["1"] == "area"
    assert chain_mapping["2"] == "family"


def test_chain_transitivity():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    aligner = ColumnAligner(
        left,
        right,
        analyzers=[JaccardAnalyzer(), AliasAnalyzer({"family": "official_family"})],
    )
    assert aligner.mapping.get("0") == "official_family"
    assert aligner.mapping.get("family") == "official_family"
