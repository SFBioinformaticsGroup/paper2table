# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import pytest

from tablemerge.analyzers import (
    AliasAnalyzer,
    HintsAnalyzer,
    JaccardAnalyzer,
    SemanticAnalyzer,
)
from tablemerge.columns_aligner import ColumnAligner
from tablevalidate.schema import Row, TableFragment
from test_columns_aligner import FOUR_COLUMNS_MAPPING, SPECIES, SPECIES_WITH_EDITS


@pytest.fixture(scope="session")
def en_spacy_model():
    import spacy

    try:
        spacy.load("en_core_web_md")
    except OSError:
        spacy.cli.download(
            "en_core_web_md"
        )  # pyright: ignore[reportAttributeAccessIssue]


@pytest.fixture(scope="session")
def es_spacy_model():
    import spacy

    try:
        spacy.load("es_core_news_md")
    except OSError:
        spacy.cli.download(
            "es_core_news_md"
        )  # pyright: ignore[reportAttributeAccessIssue]


COLOR_ANIMAL_SCHEMA = {
    "color": (str, ...),
    "animal": (str, ...),
    "identifier": (str, ...),
}
COLOR_ANIMAL_SCHEMA_ES = {
    "color": (str, ...),
    "animal": (str, ...),
    "identificador": (str, ...),
}
SPECIES_SCHEMA = {
    "scientific_name": (str, ...),
    "area": (str, ...),
    "family": (str, ...),
    "vernacular_name": (str, ...),
}


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_greedy_assignment_one_source_multiple_targets_highest_score_wins():
    analyzer = SemanticAnalyzer()
    scores = [(0.9, "0", "color"), (0.7, "0", "animal")]
    assert analyzer._greedy_assignment(scores) == {"0": "color"}


def test_greedy_assignment_multiple_sources_same_target_highest_score_wins():
    analyzer = SemanticAnalyzer()
    scores = [(0.9, "0", "color"), (0.7, "1", "color")]
    assert analyzer._greedy_assignment(scores) == {"0": "color"}


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
def test_semantic_maps_color_and_animal_columns(en_spacy_model):
    left_colors = [
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "cyan",
        "brown",
    ]
    left_animals = ["dog", "cat", "bird", "horse", "rabbit", "wolf", "deer", "fox"]
    left_codes = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"]
    right_colors = [
        "magenta",
        "violet",
        "maroon",
        "indigo",
        "turquoise",
        "crimson",
        "teal",
        "beige",
    ]
    right_animals = [
        "lion",
        "tiger",
        "bear",
        "elephant",
        "giraffe",
        "zebra",
        "monkey",
        "eagle",
    ]
    right_codes = [
        "REF001",
        "REF002",
        "REF003",
        "REF004",
        "REF005",
        "REF006",
        "REF007",
        "REF008",
    ]

    left = wrap(
        [
            Row(**{"0": color, "1": animal, "2": code})
            for color, animal, code in zip(left_colors, left_animals, left_codes)
        ]
    )
    right = wrap(
        [
            Row(color=color, animal=animal, identifier=code)
            for color, animal, code in zip(right_colors, right_animals, right_codes)
        ]
    )
    result = SemanticAnalyzer(threshold=0.3, schema=COLOR_ANIMAL_SCHEMA).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "color", "1": "animal"}


@pytest.mark.integration
def test_semantic_does_not_map_below_threshold(en_spacy_model):
    left_colors = [
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "cyan",
        "brown",
    ]
    left_animals = ["dog", "cat", "bird", "horse", "rabbit", "wolf", "deer", "fox"]
    left_codes = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"]
    right_colors = [
        "magenta",
        "violet",
        "maroon",
        "indigo",
        "turquoise",
        "crimson",
        "teal",
        "beige",
    ]
    right_animals = [
        "lion",
        "tiger",
        "bear",
        "elephant",
        "giraffe",
        "zebra",
        "monkey",
        "eagle",
    ]
    right_codes = [
        "REF001",
        "REF002",
        "REF003",
        "REF004",
        "REF005",
        "REF006",
        "REF007",
        "REF008",
    ]

    left = wrap(
        [
            Row(**{"0": color, "1": animal, "2": code})
            for color, animal, code in zip(left_colors, left_animals, left_codes)
        ]
    )
    right = wrap(
        [
            Row(color=color, animal=animal, identifier=code)
            for color, animal, code in zip(right_colors, right_animals, right_codes)
        ]
    )
    result = SemanticAnalyzer(threshold=0.99, schema=COLOR_ANIMAL_SCHEMA).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


@pytest.mark.integration
def test_semantic_maps_color_and_animal_columns_in_spanish(es_spacy_model):
    left_colors = [
        "rojo",
        "azul",
        "verde",
        "amarillo",
        "naranja",
        "morado",
        "rosa",
        "blanco",
    ]
    left_animals = [
        "perro",
        "gato",
        "pájaro",
        "caballo",
        "conejo",
        "lobo",
        "ciervo",
        "zorro",
    ]
    left_codes = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"]
    right_colors = [
        "magenta",
        "violeta",
        "marrón",
        "índigo",
        "turquesa",
        "carmesí",
        "negro",
        "gris",
    ]
    right_animals = [
        "león",
        "tigre",
        "oso",
        "elefante",
        "jirafa",
        "cebra",
        "mono",
        "águila",
    ]
    right_codes = [
        "REF001",
        "REF002",
        "REF003",
        "REF004",
        "REF005",
        "REF006",
        "REF007",
        "REF008",
    ]

    left = wrap(
        [
            Row(**{"0": color, "1": animal, "2": code})
            for color, animal, code in zip(left_colors, left_animals, left_codes)
        ]
    )
    right = wrap(
        [
            Row(color=color, animal=animal, identificador=code)
            for color, animal, code in zip(right_colors, right_animals, right_codes)
        ]
    )
    result = SemanticAnalyzer(
        threshold=0.3, language="es", schema=COLOR_ANIMAL_SCHEMA_ES
    ).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "color", "1": "animal"}


@pytest.mark.integration
def test_semantic_does_not_map_below_threshold_in_spanish(es_spacy_model):
    left_colors = [
        "rojo",
        "azul",
        "verde",
        "amarillo",
        "naranja",
        "morado",
        "rosa",
        "blanco",
    ]
    left_animals = [
        "perro",
        "gato",
        "pájaro",
        "caballo",
        "conejo",
        "lobo",
        "ciervo",
        "zorro",
    ]
    left_codes = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"]
    right_colors = [
        "magenta",
        "violeta",
        "marrón",
        "índigo",
        "turquesa",
        "carmesí",
        "negro",
        "gris",
    ]
    right_animals = [
        "león",
        "tigre",
        "oso",
        "elefante",
        "jirafa",
        "cebra",
        "mono",
        "águila",
    ]
    right_codes = [
        "REF001",
        "REF002",
        "REF003",
        "REF004",
        "REF005",
        "REF006",
        "REF007",
        "REF008",
    ]

    left = wrap(
        [
            Row(**{"0": color, "1": animal, "2": code})
            for color, animal, code in zip(left_colors, left_animals, left_codes)
        ]
    )
    right = wrap(
        [
            Row(color=color, animal=animal, identificador=code)
            for color, animal, code in zip(right_colors, right_animals, right_codes)
        ]
    )
    result = SemanticAnalyzer(
        threshold=0.99, language="es", schema=COLOR_ANIMAL_SCHEMA_ES
    ).build_mapping(
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
        left,
        right,
        analyzers=[JaccardAnalyzer(0.5), SemanticAnalyzer(0.3, schema=SPECIES_SCHEMA)],
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
        left,
        right,
        analyzers=[JaccardAnalyzer(0.6), SemanticAnalyzer(0.1, schema=SPECIES_SCHEMA)],
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


def test_hints_returns_empty_when_no_non_semantic_columns():
    left = wrap([Row(species="species", family="family")])
    right = wrap([Row(species="Ammi majus", family="Apiaceae")])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_hints_returns_empty_when_first_row_values_not_in_hints():
    left = wrap([Row(**{"0": "Ammi majus", "1": "Apiaceae"})])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_hints_renames_all_columns_when_any_value_matches_hint():
    left = wrap([Row(**{"0": "species", "1": "Apiaceae"})])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species", "1": "apiaceae"}


def test_hints_renames_columns_when_all_first_row_values_match():
    left = wrap(
        [
            Row(**{"0": "species", "1": "family"}),
            Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        ]
    )
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species", "1": "family"}


def test_hints_normalizes_first_row_values_before_comparing():
    left = wrap([Row(**{"0": "Scientific Name", "1": "Family"})])
    right = wrap([])
    result = HintsAnalyzer(["scientific_name", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "scientific_name", "1": "family"}


def test_hints_normalizes_space_separated_value_to_underscore_hint():
    left = wrap([Row(**{"1": "Scientific name"})])
    right = wrap([])
    result = HintsAnalyzer(["scientific_name"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"1": "scientific_name"}


def test_hints_normalizes_accented_value_to_ascii_hint():
    left = wrap([Row(**{"0": "Preparación"})])
    right = wrap([])
    result = HintsAnalyzer(["preparacion"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "preparacion"}


def test_hints_skips_empty_rows_before_header_row():
    left = wrap([
        Row(**{"0": "", "1": ""}),
        Row(**{"0": "", "1": ""}),
        Row(**{"0": "species", "1": "family"}),
    ])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species", "1": "family"}


def test_hints_maps_only_non_empty_hint_matching_cells_in_header_row():
    left = wrap([
        Row(**{"0": "", "1": ""}),
        Row(**{"0": "species", "1": ""}),
    ])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species"}


def test_hints_renames_all_columns_including_non_hint_values():
    left = wrap([
        Row(**{"0": "", "1": ""}),
        Row(**{"0": "species", "1": "foo"}),
    ])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species", "1": "foo"}


def test_hints_renames_all_columns_when_single_hint_matches():
    left = wrap([Row(**{
        "0": "family",
        "1": "Scientific name",
        "2": "Species",
        "3": "Notes",
    })])
    right = wrap([])
    result = HintsAnalyzer(["family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {
        "0": "family",
        "1": "scientific_name",
        "2": "species",
        "3": "notes",
    }


def test_hints_returns_empty_when_all_first_row_cells_are_empty():
    left = wrap([Row(**{"0": "", "1": ""})])
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_hints_handles_value_with_agreement_cells():
    from tablevalidate.schema import ValueWithAgreement

    left = wrap(
        [Row(**{"0": [ValueWithAgreement(value="species", agreement_level=1)]})]
    )
    right = wrap([])
    result = HintsAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "species"}
