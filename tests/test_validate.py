from datetime import datetime
from uuid import UUID
from pathlib import Path

import pytest

from tablevalidate.validate import validate_file
from tablevalidate.schema import Curation


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
