from typing import Literal

import pandas as pd

from paper2table.mapping import ColumnMapping, TableMapping, TableRowMappings
from paper2table.readers.table_mapper import TableMapper


def make_mapping(
    title="Table 1. Minor planets with high inclinations",
    header_mode: Literal["all_pages", "first_page_only", "none"] = "all_pages",
    first_page=1,
    last_page=1,
    row_mappings=None,
    column_mappings=None,
):
    if column_mappings is None:
        column_mappings = [
            ColumnMapping(from_column_number=0, to_column_name="designation"),
            ColumnMapping(from_column_number=1, to_column_name="inclination"),
        ]
    return TableMapping(
        title=title,
        header_mode=header_mode,
        first_page=first_page,
        last_page=last_page,
        row_mappings=row_mappings,
        column_mappings=column_mappings,
    )


class FakePDFTable:
    def __init__(self, rows):
        self._rows = rows

    def to_dataframe(self, column_names_hints, skip_first_row):
        return pd.DataFrame(self._rows)


def test_no_heuristics_selects_and_renames_columns():
    rows = [
        ["(65407) 2002 RP120", "118.9"],
        ["2005 VX3", "112.2"],
    ]
    mapping = make_mapping(
        header_mode="none",
        row_mappings=TableRowMappings(first_data_row=0),
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "inclination": "118.9"},
        {"designation": "2005 VX3", "inclination": "112.2"},
    ]


def test_title_removal_drops_matching_row():
    rows = [
        ["Table 1. Minor planets with high inclinations", None],
        ["(65407) 2002 RP120", "118.9"],
        ["2005 VX3", "112.2"],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(first_data_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "inclination": "118.9"},
        {"designation": "2005 VX3", "inclination": "112.2"},
    ]


def test_title_removal_drops_matching_row_when_it_is_split():
    rows = [
        ["Table 1.", "Minor planets", " with high", "inclinations"],
        ["(65407) 2002 RP120", "118.9", None, None],
        ["2005 VX3", "112.2", None, None],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(first_data_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "inclination": "118.9"},
        {"designation": "2005 VX3", "inclination": "112.2"},
    ]


def test_title_removal_keeps_unrelated_row():
    rows = [
        ["This outer-planet crosser is a damocloid", "118.9"],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(first_data_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {
            "designation": "This outer-planet crosser is a damocloid",
            "inclination": "118.9",
        },
    ]


def test_title_removal_ignores_symbols_and_case():
    rows = [
        ["TABLE 1 MINOR PLANETS WITH HIGH INCLINATIONS", None],
        ["2010 BK118", "143.9"],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(first_data_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2010 BK118", "inclination": "143.9"},
    ]


def test_row_mappings_explicit_header_row_and_first_data_row():
    rows = [
        ["Minor planet designation", "Inclination"],
        ["(65407) 2002 RP120", "118.9"],
        ["2005 VX3", "112.2"],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "inclination": "118.9"},
        {"designation": "2005 VX3", "inclination": "112.2"},
    ]


def test_row_mappings_first_data_row_defaults_to_header_row_plus_one():
    rows = [
        ["Minor planet designation", "Inclination"],
        ["2010 BK118", "143.9"],
    ]
    mapping = make_mapping(
        row_mappings=TableRowMappings(header_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2010 BK118", "inclination": "143.9"},
    ]


def test_from_column_name_exact_match():
    rows = [
        ["Minor planet designation", "Inclination (°)"],
        ["(65407) 2002 RP120", "118.9"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination (°)",
                from_column_number=1,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "inclination": "118.9"},
    ]


def test_from_column_name_single_accumulation():
    rows = [
        ["Minor planet desig", "nation", "Inclination"],
        ["(65407) 2002 RP120", "suffix", "118.9"],
        ["2005 VX3", "cont", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_from_column_name_multiple_accumulations():
    rows = [
        ["Designation", "First obse", "rved/Discove", "ry date"],
        ["2002 RP120", "September 4,", "2002", None],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="First observed/Discovery date",
                from_column_number=1,
                to_column_name="discovery_date",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2002 RP120", "discovery_date": "September 4, 2002"},
    ]


def test_from_column_name_multiple_accumulations_handling_spaces_in_header():
    rows = [
        ["Designation", "First observed", "/Discovery", "date"],
        ["2002 RP120", "September 4, 2002", "", ""],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="First observed/Discovery date",
                from_column_number=1,
                to_column_name="discovery_date",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2002 RP120", "discovery_date": "September 4, 2002"},
    ]

def test_from_column_name_multiple_accumulations_in_multiple_columns():
    rows = [
        ["Designation", "First observed", "/Disco", "very date", "REF", "ERENCE"],
        ["2002 RP120", "September 4, 2002", "", "", "1", "-1"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="First observed/Discovery date",
                from_column_number=1,
                to_column_name="discovery_date",
            ),
            ColumnMapping(
                from_column_name="REFERENCE",
                from_column_number=2,
                to_column_name="reference",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2002 RP120", "discovery_date": "September 4, 2002", "reference": "1-1"},
    ]



def test_from_column_name_fallback_when_no_match():
    rows = [
        ["Desig", "nati", "on", "extra", "more", "stuff", "Inclination"],
        [
            "2002 RP120",
            "ignored1",
            "ignored2",
            "ignored3",
            "ignored4",
            "ignored5",
            "118.9",
        ],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_number=6,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "2002 RP120", "inclination": "118.9"},
    ]


def test_from_column_name_absent_uses_column_number():
    rows = [
        ["(65407) 2002 RP120", "118.9", "September 4, 2002"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(from_column_number=0, to_column_name="designation"),
            ColumnMapping(from_column_number=2, to_column_name="discovery_date"),
        ],
        row_mappings=TableRowMappings(first_data_row=0),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120", "discovery_date": "September 4, 2002"},
    ]


def test_combined_title_removal_row_mappings_and_column_accumulation():
    rows = [
        # Title row
        ["Table 1. Minor planets with high inclinations", None, None],
        # header_row=0 after Jaccard removal
        ["Minor planet desig", "nation", "Inclination"],
        # Data rows
        ["(65407) 2002 RP120", "suffix", "118.9"],
        ["2005 VX3", "cont", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_combined_title_removal_row_mappings_and_column_accumulation_with_blank_lines():
    rows = [
        ["", "", ""],
        ["Table 1. Minor planets with", "high", "inclinations"],
        ["", "", ""],
        ["Minor planet desig", "nation", "Inclination"],
        ["", "", ""],
        ["(65407) 2002 RP120", "suffix", "118.9"],
        ["", "", ""],
        ["2005 VX3", "cont", "112.2"],
        ["", "", ""],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_combined_title_removal_row_mappings_and_column_accumulation_with_paddings():
    rows = [
        ["", "Table 1. Minor planets with", "high", "", "inclinations"],
        ["", "Minor planet desig", "nation", "", "Inclination"],
        ["", "(65407) 2002 RP120", "suffix", "", "118.9"],
        ["", "2005 VX3", "cont", "", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_combined_title_removal_row_mappings_and_column_accumulation_with_paddings_in_headers():
    rows = [
        ["", "Table 1. Minor planets with", "high", "", "inclinations"],
        ["", "Minor planet desig", "nation", "", "Inclination"],
        ["", "(65407) 2002", "RP120", "suffix", "118.9"],
        ["", "2005 VX3", "cont", "", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_combined_title_removal_row_mappings_and_column_accumulation_with_paddings_only_but_no_on_title():
    rows = [
        ["Table 1. Minor planets with", "high", "", "inclinations"],
        ["", "Minor planet desig", "nation", "", "Inclination"],
        ["", "(65407) 2002 RP120", "suffix", "", "118.9"],
        ["", "2005 VX3", "cont", "", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]


def test_combined_row_mappings_and_column_accumulation_with_noisy_trailing_lines():
    rows = [
        # Noisy rows at start before rows with column names
        ["...", "...", "..."],
        ["...", None, None],
        ["(cont...)", None, None],
        ["Copyright", "2001", None],
        ["Some more", "random", "text"],
        ["Minor planet desig", "nation", "Inclination"],
        ["(65407) 2002 RP120", "suffix", "118.9"],
        ["2005 VX3", "cont", "112.2"],
    ]
    mapping = make_mapping(
        column_mappings=[
            ColumnMapping(
                from_column_name="Minor planet designation",
                from_column_number=0,
                to_column_name="designation",
            ),
            ColumnMapping(
                from_column_name="Inclination",
                from_column_number=2,
                to_column_name="inclination",
            ),
        ],
        row_mappings=TableRowMappings(header_row=0, first_data_row=1),
        header_mode="none",
    )
    result = TableMapper(mapping).transform([FakePDFTable(rows)], page_number=1)
    assert result.to_dict(orient="records") == [
        {"designation": "(65407) 2002 RP120 suffix", "inclination": "118.9"},
        {"designation": "2005 VX3 cont", "inclination": "112.2"},
    ]
