from datetime import datetime
from uuid import UUID

import pytest

from paper2table.writers.tablemerge import TablemergeMetadata


def test_uuid_is_unique():
    m1 = TablemergeMetadata("camelot", "model1")
    m2 = TablemergeMetadata("camelot", "model2")
    assert m1.uuid != m2.uuid


def test_to_dict_regular_reader():
    meta = TablemergeMetadata(reader="camelot", model="test-model")
    d = meta.to_dict()

    assert d["reader"] == "camelot"
    assert UUID(d["uuid"])
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)


def test_to_dict_reader_agent_substitutes_model():
    meta = TablemergeMetadata(reader="agent", model="special-model")
    d = meta.to_dict()

    assert d["reader"] == "special-model"
    assert UUID(d["uuid"])
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)


def test_to_dict_reader_agent_with_none_model():
    meta = TablemergeMetadata(reader="agent", model=None)
    d = meta.to_dict()

    assert d["reader"] is None
    assert UUID(d["uuid"])
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)
