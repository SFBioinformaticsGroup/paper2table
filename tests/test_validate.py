from datetime import datetime
from uuid import UUID
from pathlib import Path

import pytest

from tablevalidate.validate import validate_file
from tablevalidate.schema import Curation, Row, TablesFile, TableWithFragments, TableFragment


def test_can_validate_valid_file():
    validate_file(
        Path(
            "./tests/data/demo_resultsets/39c01438-4af8-4f2a-ac5d-278b9653f565/extended_overview.tables.json"
        )
    )


def test_curation_requires_name():
    curation = Curation(curator="Umi")
    assert curation.curator == "Umi"
    assert curation.description is None
    assert curation.timestamp is None


def test_curation_with_description():
    curation = Curation(curator="Umi", description="Corregida estructura")
    assert curation.curator == "Umi"
    assert curation.description == "Corregida estructura"
    assert curation.timestamp is None


def test_curation_with_date():
    curation = Curation(curator="Umi", timestamp="2026-06-25")
    assert curation.curator == "Umi"
    assert curation.timestamp == "2026-06-25"
    assert curation.description is None


def test_curation_with_all_fields():
    curation = Curation(
        curator="Umi",
        description="Corregida estructura",
        timestamp="2026-06-25",
    )
    assert curation.curator == "Umi"
    assert curation.description == "Corregida estructura"
    assert curation.timestamp == "2026-06-25"


def test_row_accepts_int_column_value():
    row = Row(count=42)
    assert row.get_columns() == {"count": 42}


def test_row_accepts_float_column_value():
    row = Row(ratio=3.14)
    assert row.get_columns() == {"ratio": 3.14}


def test_row_accepts_bool_false_column_value():
    row = Row(active=False)
    assert row.get_columns() == {"active": False}


def test_row_accepts_bool_true_column_value():
    row = Row(active=True)
    assert row.get_columns() == {"active": True}


def test_tablesfile_model_validate_accepts_int_cell():
    data = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"count": 42}]}],
    }
    tablesfile = TablesFile.model_validate(data)
    assert tablesfile.tables[0].get_table_fragments()[0].rows[0].get_columns() == {"count": 42}


def test_tablesfile_model_validate_accepts_float_cell():
    data = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"ratio": 3.14}]}],
    }
    tablesfile = TablesFile.model_validate(data)
    assert tablesfile.tables[0].get_table_fragments()[0].rows[0].get_columns() == {"ratio": 3.14}


def test_tablesfile_model_validate_accepts_bool_cell():
    data = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"active": True}]}],
    }
    tablesfile = TablesFile.model_validate(data)
    assert tablesfile.tables[0].get_table_fragments()[0].rows[0].get_columns() == {"active": True}


def test_tablesfile_model_validate_bool_false_not_treated_as_empty():
    data = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"active": False}]}],
    }
    tablesfile = TablesFile.model_validate(data)
    row = tablesfile.tables[0].get_table_fragments()[0].rows[0]
    assert row.is_empty() is False
