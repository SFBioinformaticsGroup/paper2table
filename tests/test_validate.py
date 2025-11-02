from datetime import datetime
from uuid import UUID
from pathlib import Path

import pytest

from tablevalidate.validate import validate_file


def test_can_validate_valid_file():
    validate_file(
        Path(
            "./tests/data/demo_resultsets/39c01438-4af8-4f2a-ac5d-278b9653f565/extended_overview.tables.json"
        )
    )
