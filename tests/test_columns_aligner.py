# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import pytest

from tablemerge.analyzers import AliasAnalyzer, JaccardAnalyzer
from tablemerge.columns_aligner import LoadTimeColumnAligner, MergeTimeColumnAligner
from tablevalidate.schema import (
    Row,
    TableFragment,
)


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_column_aligner_right_numeric_to_left_semantic():
    left = wrap(
        [
            Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
            Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
            Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
        ]
    )
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {
        "0": "family",
        "1": "scientific_name",
    }


def test_column_aligner_left_numeric_to_right_semantic():
    left = wrap(
        [
            Row(**{"0": "lunes", "1": "monday"}),
            Row(**{"0": "martes", "1": "tuesday"}),
        ]
    )
    right = wrap(
        [
            Row(**{"dia": "lunes", "day": "monday"}),
            Row(**{"dia": "martes", "day": "tuesday"}),
        ]
    )
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {
        "0": "dia",
        "1": "day",
    }


def test_column_aligner_both_semantic_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {}


def test_column_aligner_both_numeric_returns_empty():
    left = wrap([Row(**{"0": "Apiaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {}


def test_column_aligner_no_value_overlap_returns_empty():
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "red"}),
            Row(**{"0": "blue"}),
        ]
    )
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {}


def test_column_aligner_partial_overlap_above_threshold():
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae"}),
        ]
    )
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {
        "0": "family"
    }


@pytest.mark.parametrize(
    "threshold,expected",
    [
        (0.6, {}),
        (0.5, {"0": "family"}),
        (0.4, {"0": "family"}),
    ],
)
def test_column_aligner_threshold(threshold, expected):
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert (
        MergeTimeColumnAligner(
            left, right, analyzers=[JaccardAnalyzer(threshold=threshold)]
        ).mapping
        == expected
    )


def test_column_aligner_empty_fragment():
    left = wrap([])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {}


def test_column_aligner_one_col_matches_one_does_not():
    left = wrap(
        [
            Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
            Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae", "1": "zzz"}),
            Row(**{"0": "Rosaceae", "1": "www"}),
        ]
    )
    assert MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()]).mapping == {
        "0": "family"
    }


def test_column_aligner_none_right_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    assert MergeTimeColumnAligner(left, None, analyzers=[JaccardAnalyzer()]).mapping == {}


def test_column_aligner_rename_maps_numeric_to_semantic():
    left = wrap([Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."})])
    right = wrap([Row(**{"0": "Apiaceae", "1": "Ammi majus L."})])
    aligner = MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()])
    assert aligner.rename_column("0") == "family"
    assert aligner.rename_column("1") == "scientific_name"
    assert aligner.rename_column("family") == "family"


def test_column_aligner_rename_row_renames_columns():
    left = wrap([Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."})])
    right = wrap([Row(**{"0": "Apiaceae", "1": "Ammi majus L."})])
    aligner = MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()])
    row = Row(**{"0": "Rosaceae", "1": "Rosa canina L."})
    assert aligner.rename_row(row) == Row(
        family="Rosaceae", scientific_name="Rosa canina L."
    )


def test_column_aligner_rename_row_noop_when_no_mapping():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    aligner = MergeTimeColumnAligner(left, right, analyzers=[JaccardAnalyzer()])
    row = Row(family="Rosaceae")
    assert aligner.rename_row(row) is row


SPECIES = [
    ("Ammi majus L.", "45.2", "Apiaceae", "Greater ammi"),
    ("Rosa canina L.", "12.8", "Rosaceae", "Dog rose"),
    ("Mentha spicata L.", "67.3", "Lamiaceae", "Spearmint"),
    ("Betula pendula Roth", "89.1", "Betulaceae", "Silver birch"),
    ("Quercus robur L.", "23.4", "Fagaceae", "English oak"),
    ("Taraxacum officinale F.H.Wigg.", "56.7", "Asteraceae", "Dandelion"),
    ("Urtica dioica L.", "34.9", "Urticaceae", "Stinging nettle"),
    ("Sambucus nigra L.", "78.2", "Adoxaceae", "Black elder"),
    ("Hypericum perforatum L.", "41.5", "Hypericaceae", "St John's wort"),
    ("Achillea millefolium L.", "93.6", "Asteraceae", "Yarrow"),
    ("Plantago lanceolata L.", "17.3", "Plantaginaceae", "Ribwort plantain"),
    ("Matricaria chamomilla L.", "52.8", "Asteraceae", "German chamomile"),
    ("Lavandula angustifolia Mill.", "61.4", "Lamiaceae", "Lavender"),
    ("Rosmarinus officinalis L.", "38.7", "Lamiaceae", "Rosemary"),
    ("Thymus vulgaris L.", "25.1", "Lamiaceae", "Common thyme"),
    ("Origanum vulgare L.", "72.9", "Lamiaceae", "Oregano"),
    ("Salvia officinalis L.", "44.6", "Lamiaceae", "Common sage"),
    ("Foeniculum vulgare Mill.", "83.2", "Apiaceae", "Fennel"),
    ("Melissa officinalis L.", "19.5", "Lamiaceae", "Lemon balm"),
    ("Echinacea purpurea (L.) Moench", "67.8", "Asteraceae", "Purple coneflower"),
]

SPECIES_WITH_EDITS = [
    ("Ammi majus", "45.2", "Apiaceae", "Greater ammi spp."),
    ("Rosa canina, L.", "12.8", "Rosaceae", "Dog-rose"),
    ("Mentha spicata", "67.3", "Lamiaceae", "Spearmint herb"),
    ("Betula pendula Rot", "89.1", "Betulaceae", "Silver-birch"),
    ("Quercus robur", "23.4", "Fagaceae", "Eng. oak"),
    ("T. officinale F.H.Wigg.", "56.7", "Asteraceae", "Dandelyon"),
    *SPECIES[6:],
]

FOUR_COLUMNS_MAPPING = {
    "0": "scientific_name",
    "1": "area",
    "2": "family",
    "3": "vernacular_name",
}


@pytest.mark.parametrize("threshold", [0.3, 0.4, 0.5, 0.6])
def test_column_aligner_four_columns_exact(threshold):
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
    assert (
        MergeTimeColumnAligner(
            left, right, analyzers=[JaccardAnalyzer(threshold=threshold)]
        ).mapping
        == FOUR_COLUMNS_MAPPING
    )


@pytest.mark.parametrize(
    "threshold,expected",
    [
        (0.3, FOUR_COLUMNS_MAPPING),
        (0.4, FOUR_COLUMNS_MAPPING),
        (0.5, FOUR_COLUMNS_MAPPING),
        (0.6, {"1": "area", "2": "family"}),
    ],
)
def test_column_aligner_four_columns_with_text_edits(threshold, expected):
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
    assert (
        MergeTimeColumnAligner(
            left, right, analyzers=[JaccardAnalyzer(threshold=threshold)]
        ).mapping
        == expected
    )


@pytest.mark.parametrize("threshold", [0.3, 0.4, 0.5, 0.6])
def test_column_aligner_four_columns_partial_column_match(threshold):
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
            Row(
                **{
                    "0": scientific_name,
                    "1": area,
                    "2": f"REF{i:04d}",
                    "3": vernacular_name,
                }
            )
            for i, (scientific_name, area, family, vernacular_name) in enumerate(
                SPECIES
            )
        ]
    )
    assert MergeTimeColumnAligner(
        left, right, analyzers=[JaccardAnalyzer(threshold=threshold)]
    ).mapping == {
        "0": "scientific_name",
        "1": "area",
        "3": "vernacular_name",
    }


def test_column_aligner_with_alias_on_semantic_to_semantic():
    left = wrap([Row(**{"familia": "Apiaceae"}), Row(**{"familia": "Rosaceae"})])
    aligner = LoadTimeColumnAligner(left, analyzers=[AliasAnalyzer({"familia": "family"})])
    assert aligner.mapping == {"familia": "family"}


def test_column_aligner_alias_before_jaccard():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    load_aligner = LoadTimeColumnAligner(
        left, analyzers=[AliasAnalyzer({"family": "official_family"})]
    )
    assert load_aligner.mapping == {"family": "official_family"}
    renamed_left = TableFragment(
        rows=[load_aligner.rename_row(r) for r in left.rows], page=left.page
    )
    merge_aligner = MergeTimeColumnAligner(renamed_left, right, analyzers=[JaccardAnalyzer()])
    assert merge_aligner.mapping == {"0": "official_family"}


def test_column_aligner_alias_applies_without_right_fragment():
    left = wrap([Row(**{"familia": "Apiaceae"}), Row(**{"familia": "Rosaceae"})])
    aligner = LoadTimeColumnAligner(left, analyzers=[AliasAnalyzer({"familia": "family"})])
    assert aligner.mapping == {"familia": "family"}


def test_column_aligner_jaccard_no_op_without_right_fragment():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    aligner = MergeTimeColumnAligner(left, None, analyzers=[JaccardAnalyzer()])
    assert aligner.mapping == {}
