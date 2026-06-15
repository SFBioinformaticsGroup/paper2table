# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import pytest

from tablemerge.analyzers import (
    AliasLoadTimeAnalyzer,
    ColumnNameSemanticLoadTimeAnalyzer,
    ColumnValueSemanticMergeTimeAnalyzer,
    HintsLoadTimeAnalyzer,
    JaccardMergeTimeAnalyzer,
    REMOVE_COLUMN,
    column_value_to_strings,
)
from tablemerge.columns_aligner import LoadTimeColumnAligner, MergeTimeColumnAligner
from tablevalidate.schema import Row, TableFragment, ValueWithAgreement
from utils.column_schema import ColumnSchema
from test_columns_aligner import FOUR_COLUMNS_MAPPING, SPECIES, SPECIES_WITH_EDITS


@pytest.fixture(scope="session")
def en_spacy_model():
    import spacy

    try:
        spacy.load("en_core_web_md")
    except OSError:
        spacy.cli.download(  # pyright: ignore[reportAttributeAccessIssue]
            "en_core_web_md"
        )


@pytest.fixture(scope="session")
def es_spacy_model():
    import spacy

    try:
        spacy.load("es_core_news_md")
    except OSError:
        spacy.cli.download(  # pyright: ignore[reportAttributeAccessIssue]
            "es_core_news_md"
        )


COLOR_ANIMAL_SCHEMA = ColumnSchema({"color": str, "animal": str, "identifier": str})
COLOR_ANIMAL_SCHEMA_ES = ColumnSchema(
    {"color": str, "animal": str, "identificador": str}
)
SPECIES_SCHEMA = ColumnSchema(
    {"scientific_name": str, "area": str, "family": str, "vernacular_name": str}
)


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_greedy_assignment_one_source_multiple_targets_highest_score_wins():
    analyzer = ColumnNameSemanticLoadTimeAnalyzer()
    scores = [(0.9, "0", "color"), (0.7, "0", "animal")]
    assert analyzer._greedy_assignment(scores) == {"0": "color"}


def test_greedy_assignment_multiple_sources_same_target_highest_score_wins():
    analyzer = ColumnNameSemanticLoadTimeAnalyzer()
    scores = [(0.9, "0", "color"), (0.7, "1", "color")]
    assert analyzer._greedy_assignment(scores) == {"0": "color"}


def test_jaccard_numeric_to_semantic():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    result = JaccardMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "family"}


def test_jaccard_both_semantic_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = JaccardMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_no_overlap_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"0": "red"})])
    result = JaccardMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_threshold_respected():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert JaccardMergeTimeAnalyzer(threshold=0.5).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    ) == {"0": "family"}
    assert (
        JaccardMergeTimeAnalyzer(threshold=0.6).build_mapping(
            left.get_column_names(), right.get_column_names(), left.rows, right.rows
        )
        == {}
    )


def test_alias_applies_known_alias():
    result = AliasLoadTimeAnalyzer({"familia": "family"}).build_mapping(
        ["familia", "family"], []
    )
    assert result == {"familia": "family"}


def test_alias_ignores_unknown_cols():
    result = AliasLoadTimeAnalyzer({"familia": "family"}).build_mapping(
        ["genus", "family"], []
    )
    assert result == {}


def test_alias_maps_multiple_columns():
    result = AliasLoadTimeAnalyzer(
        {"familia": "family", "especie": "species"}
    ).build_mapping(["familia", "especie"], [])
    assert result == {"familia": "family", "especie": "species"}


def test_alias_deduplicates_duplicate_column_names():
    result = AliasLoadTimeAnalyzer({"familia": "family"}).build_mapping(
        ["familia", "familia"], []
    )
    assert result == {"familia": "family"}


def test_alias_remove_column_produces_remove_sentinel():
    result = AliasLoadTimeAnalyzer({"notes": REMOVE_COLUMN}).build_mapping(
        ["family", "notes"], []
    )
    assert result == {"notes": REMOVE_COLUMN}


def test_alias_remove_column_drops_column_from_row():
    fragment = wrap([Row(**{"family": "Apiaceae", "notes": "some note"})])
    aligner = LoadTimeColumnAligner(
        fragment,
        analyzers=[AliasLoadTimeAnalyzer({"notes": REMOVE_COLUMN})],
    )
    assert aligner.rename_row(fragment.rows[0]) == Row(family="Apiaceae")


def test_alias_remove_column_keeps_other_columns_intact():
    fragment = wrap([Row(**{"family": "Apiaceae", "genus": "Ammi", "notes": "x"})])
    aligner = LoadTimeColumnAligner(
        fragment,
        analyzers=[AliasLoadTimeAnalyzer({"notes": REMOVE_COLUMN})],
    )
    assert aligner.rename_row(fragment.rows[0]) == Row(family="Apiaceae", genus="Ammi")


def test_semantic_returns_empty_when_both_numeric():
    left = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    right = wrap([Row(**{"1": "Apiaceae"}), Row(**{"1": "Rosaceae"})])
    result = ColumnNameSemanticLoadTimeAnalyzer().build_mapping(
        left.get_column_names() + right.get_column_names(), left.rows
    )
    assert result == {}


def test_semantic_returns_empty_when_both_semantic():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = ColumnNameSemanticLoadTimeAnalyzer().build_mapping(
        left.get_column_names() + right.get_column_names(), left.rows
    )
    assert result == {}


def test_semantic_returns_empty_when_numeric_rows_are_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    result = ColumnNameSemanticLoadTimeAnalyzer().build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_semantic_returns_empty_both_numeric_species_data():
    rows = [
        Row(**{"0": scientific_name, "1": area, "2": family, "3": vernacular_name})
        for scientific_name, area, family, vernacular_name in SPECIES
    ]
    left = wrap(rows)
    result = ColumnNameSemanticLoadTimeAnalyzer().build_mapping(
        left.get_column_names(), left.rows
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
    result = ColumnNameSemanticLoadTimeAnalyzer().build_mapping(
        left.get_column_names(), left.rows
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
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.3, schema=COLOR_ANIMAL_SCHEMA
    ).build_mapping(left.get_column_names(), left.rows)
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
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.99, schema=COLOR_ANIMAL_SCHEMA
    ).build_mapping(left.get_column_names(), left.rows)
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
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.3, language="es", schema=COLOR_ANIMAL_SCHEMA_ES
    ).build_mapping(left.get_column_names(), left.rows)
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
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.99, language="es", schema=COLOR_ANIMAL_SCHEMA_ES
    ).build_mapping(left.get_column_names(), left.rows)
    assert result == {}


@pytest.mark.integration
def test_semantic_maps_semantic_not_in_schema_columns(en_spacy_model):
    colors = ["red", "blue", "green", "yellow", "orange", "purple", "cyan", "brown"]
    animals = ["dog", "cat", "bird", "horse", "rabbit", "wolf", "deer", "fox"]
    fragment = wrap(
        [
            Row(**{"animalia": color, "tone": animal})
            for color, animal in zip(colors, animals)
        ]
    )
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.3, schema=COLOR_ANIMAL_SCHEMA
    ).build_mapping(fragment.get_column_names(), fragment.rows)
    assert result == {"animalia": "color", "tone": "animal"}


@pytest.mark.integration
def test_semantic_does_not_rename_semantic_column_when_own_name_is_closer(en_spacy_model):
    dog_breeds = [
        "poodle", "labrador", "beagle", "bulldog", "terrier",
        "husky", "boxer", "dachshund",
    ]
    fragment = wrap([Row(**{"dog": breed}) for breed in dog_breeds])
    schema = ColumnSchema({"canine": str})
    result = ColumnNameSemanticLoadTimeAnalyzer(
        threshold=0.3, schema=schema
    ).build_mapping(fragment.get_column_names(), fragment.rows)
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
    load_aligner = LoadTimeColumnAligner(
        left, analyzers=[ColumnNameSemanticLoadTimeAnalyzer(0.3, schema=SPECIES_SCHEMA)]
    )
    renamed_left = TableFragment(
        rows=[load_aligner.rename_row(r) for r in left.rows], page=left.page
    )
    merge_aligner = MergeTimeColumnAligner(
        renamed_left, right, analyzers=[JaccardMergeTimeAnalyzer(0.5)]
    )
    assert merge_aligner.mapping == FOUR_COLUMNS_MAPPING


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
    jaccard_mapping = MergeTimeColumnAligner(
        left, right, analyzers=[JaccardMergeTimeAnalyzer(0.6)]
    ).mapping
    assert jaccard_mapping == {"1": "area", "2": "family"}

    load_aligner = LoadTimeColumnAligner(
        left, analyzers=[ColumnNameSemanticLoadTimeAnalyzer(0.1, schema=SPECIES_SCHEMA)]
    )
    renamed_left = TableFragment(
        rows=[load_aligner.rename_row(r) for r in left.rows], page=left.page
    )
    chain_mapping = MergeTimeColumnAligner(
        renamed_left, right, analyzers=[JaccardMergeTimeAnalyzer(0.6)]
    ).mapping
    assert chain_mapping["1"] == "area"
    assert chain_mapping["2"] == "family"


def test_chain_alias_before_jaccard():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    load_aligner = LoadTimeColumnAligner(
        left, analyzers=[AliasLoadTimeAnalyzer({"family": "official_family"})]
    )
    assert load_aligner.mapping == {"family": "official_family"}
    renamed_left = TableFragment(
        rows=[load_aligner.rename_row(r) for r in left.rows], page=left.page
    )
    merge_aligner = MergeTimeColumnAligner(
        renamed_left, right, analyzers=[JaccardMergeTimeAnalyzer()]
    )
    assert merge_aligner.mapping == {"0": "official_family"}


def test_chain_hints_then_alias_renames_through_intermediate_name():
    fragment = wrap([Row(**{"0": "species"})])
    aligner = LoadTimeColumnAligner(
        fragment,
        analyzers=[
            HintsLoadTimeAnalyzer(["species"]),
            AliasLoadTimeAnalyzer({"species": "scientific_name"}),
        ],
    )
    assert aligner.mapping == {"0": "scientific_name", "species": "scientific_name"}


def test_hints_returns_empty_when_no_non_semantic_columns():
    left = wrap([Row(species="species", family="family")])
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_hints_returns_empty_when_first_row_values_not_in_hints():
    left = wrap([Row(**{"0": "Ammi majus", "1": "Apiaceae"})])
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_hints_renames_all_columns_when_any_value_matches_hint():
    left = wrap([Row(**{"0": "species", "1": "Apiaceae"})])
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species", "1": "apiaceae"}


def test_hints_renames_columns_when_all_first_row_values_match():
    left = wrap(
        [
            Row(**{"0": "species", "1": "family"}),
            Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        ]
    )
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species", "1": "family"}


def test_hints_normalizes_first_row_values_before_comparing():
    left = wrap([Row(**{"0": "Scientific Name", "1": "Family"})])
    result = HintsLoadTimeAnalyzer(["scientific_name", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "scientific_name", "1": "family"}


def test_hints_normalizes_space_separated_value_to_underscore_hint():
    left = wrap([Row(**{"1": "Scientific name"})])
    result = HintsLoadTimeAnalyzer(["scientific_name"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"1": "scientific_name"}


def test_hints_normalizes_accented_value_to_ascii_hint():
    left = wrap([Row(**{"0": "Preparación"})])
    result = HintsLoadTimeAnalyzer(["preparacion"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "preparacion"}


def test_hints_skips_empty_rows_before_header_row():
    left = wrap(
        [
            Row(**{"0": "", "1": ""}),
            Row(**{"0": "", "1": ""}),
            Row(**{"0": "species", "1": "family"}),
        ]
    )
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species", "1": "family"}


def test_hints_maps_only_non_empty_hint_matching_cells_in_header_row():
    left = wrap(
        [
            Row(**{"0": "", "1": ""}),
            Row(**{"0": "species", "1": ""}),
        ]
    )
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species"}


def test_hints_renames_all_columns_including_non_hint_values():
    left = wrap(
        [
            Row(**{"0": "", "1": ""}),
            Row(**{"0": "species", "1": "foo"}),
        ]
    )
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species", "1": "foo"}


def test_hints_renames_all_columns_when_single_hint_matches():
    left = wrap(
        [
            Row(
                **{
                    "0": "family",
                    "1": "Scientific name",
                    "2": "Species",
                    "3": "Notes",
                }
            )
        ]
    )
    result = HintsLoadTimeAnalyzer(["family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {
        "0": "family",
        "1": "scientific_name",
        "2": "species",
        "3": "notes",
    }


def test_hints_skips_null_column_when_other_columns_trigger_mapping():
    left = wrap(
        [
            Row(
                **{
                    "0": "family",
                    "1": "Scientific name",
                    "2": "species",
                    "3": None,
                }
            )
        ]
    )
    result = HintsLoadTimeAnalyzer(["family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {
        "0": "family",
        "1": "scientific_name",
        "2": "species",
    }


def test_hints_returns_empty_when_all_first_row_cells_are_empty():
    left = wrap([Row(**{"0": "", "1": ""})])
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_hints_handles_value_with_agreement_cells():
    left = wrap(
        [Row(**{"0": [ValueWithAgreement(value="species", agreement_level=1)]})]
    )
    result = HintsLoadTimeAnalyzer(["species", "family"]).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species"}


def test_hints_unsafe_renames_semantic_columns_when_values_match_hints():
    left = wrap([Row(species="species", family="family")])
    result = HintsLoadTimeAnalyzer(["species", "family"], safe=False).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"species": "species", "family": "family"}


def test_hints_unsafe_renames_mix_of_semantic_and_numeric_columns():
    left = wrap([Row(**{"0": "species", "family": "family"})])
    result = HintsLoadTimeAnalyzer(["species", "family"], safe=False).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {"0": "species", "family": "family"}


def test_hints_safe_still_returns_empty_when_all_columns_are_semantic():
    left = wrap([Row(species="species", family="family")])
    result = HintsLoadTimeAnalyzer(["species", "family"], safe=True).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_hints_unsafe_returns_empty_when_no_rows_match_hints():
    left = wrap([Row(species="Ammi majus", family="Apiaceae")])
    result = HintsLoadTimeAnalyzer(["species", "family"], safe=False).build_mapping(
        left.get_column_names(), left.rows
    )
    assert result == {}


def test_column_value_to_strings_returns_empty_for_none():
    assert column_value_to_strings(None) == []


def test_extract_column_str_values_returns_empty_for_none():
    assert JaccardMergeTimeAnalyzer().extract_column_str_values(None) == []


def test_jaccard_renames_semantic_not_in_schema_to_schema_column():
    schema = ColumnSchema({"family": str})
    left = wrap([Row(**{"familia": "Apiaceae"}), Row(**{"familia": "Rosaceae"})])
    right = wrap([Row(family="Apiaceae"), Row(family="Rosaceae")])
    result = JaccardMergeTimeAnalyzer(schema=schema).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"familia": "family"}


def test_jaccard_renames_semantic_not_in_schema_to_schema_column_with_partial_overlap():
    schema = ColumnSchema({"family": str})
    left = wrap([
        Row(**{"familia": "Apiaceae"}),
        Row(**{"familia": "Rosaceae"}),
        Row(**{"familia": "Lamiaceae"}),
    ])
    right = wrap([
        Row(family="Apiaceae"),
        Row(family="Rosaceae"),
        Row(family="Asteraceae"),
    ])
    result = JaccardMergeTimeAnalyzer(schema=schema).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"familia": "family"}


def test_jaccard_both_out_of_schema_with_schema_returns_empty():
    schema = ColumnSchema({"family": str})
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"especie": "Ammi"})])
    result = JaccardMergeTimeAnalyzer(schema=schema).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_schema_column_not_renamed_even_with_schema():
    schema = ColumnSchema({"family": str})
    left = wrap([Row(family="Apiaceae"), Row(family="Rosaceae")])
    right = wrap([Row(family="Apiaceae"), Row(family="Rosaceae")])
    result = JaccardMergeTimeAnalyzer(schema=schema).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_column_value_semantic_returns_empty_when_both_numeric():
    left = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    right = wrap([Row(**{"1": "Apiaceae"}), Row(**{"1": "Rosaceae"})])
    result = ColumnValueSemanticMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_column_value_semantic_returns_empty_when_both_semantic():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = ColumnValueSemanticMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


def test_column_value_semantic_returns_empty_when_left_has_mixed_columns():
    left = wrap([Row(**{"0": "Apiaceae", "family": "Rosaceae"})])
    right = wrap([Row(**{"1": "Ammi"})])
    result = ColumnValueSemanticMergeTimeAnalyzer().build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {}


@pytest.mark.integration
def test_column_value_semantic_maps_numeric_to_semantic_by_value_similarity(
    en_spacy_model,
):
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
    left = wrap(
        [
            Row(color=color, animal=animal)
            for color, animal in zip(left_colors, left_animals)
        ]
    )
    right = wrap(
        [
            Row(**{"0": color, "1": animal})
            for color, animal in zip(right_colors, right_animals)
        ]
    )
    result = ColumnValueSemanticMergeTimeAnalyzer(threshold=0.3).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"0": "color", "1": "animal"}


@pytest.mark.integration
def test_column_value_semantic_renames_semantic_not_in_schema_to_schema_column(
    en_spacy_model,
):
    schema = ColumnSchema({"color": str, "animal": str})
    colors = ["red", "blue", "green", "yellow", "orange", "purple", "cyan", "brown"]
    animals = ["dog", "cat", "bird", "horse", "rabbit", "wolf", "deer", "fox"]
    left = wrap(
        [Row(color=color, animal=animal) for color, animal in zip(colors, animals)]
    )
    right = wrap(
        [
            Row(**{"animalia": color, "tone": animal})
            for color, animal in zip(colors, animals)
        ]
    )
    result = ColumnValueSemanticMergeTimeAnalyzer(threshold=0.3, schema=schema).build_mapping(
        left.get_column_names(), right.get_column_names(), left.rows, right.rows
    )
    assert result == {"animalia": "color", "tone": "animal"}
