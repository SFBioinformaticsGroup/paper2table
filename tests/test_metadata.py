from datetime import datetime
from uuid import UUID

import pytest

from paper2table.writers.tablemerge import TablemergeMetadata



def test_to_dict_regular_reader():
    meta = TablemergeMetadata(reader="camelot", model="test-model", id="test")
    d = meta.to_dict()

    assert d["reader"] == "camelot"
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)


def test_to_dict_reader_agent_substitutes_model():
    meta = TablemergeMetadata(reader="agent", model="special-model", id="test")
    d = meta.to_dict()

    assert d["reader"] == "special-model"
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)


def test_to_dict_reader_hybrid():
    meta = TablemergeMetadata(reader="pdfplumber", model="custom", id="test", hybrid=True)
    d = meta.to_dict()

    assert d["reader"] == "hybrid-pdfplumber-custom"
    assert isinstance(datetime.fromisoformat(d["datetime"]), datetime)
