import argparse

import pytest

from utils.cli import add_na_values_args
from utils.column_values import (
    DEFAULT_NA_VALUES,
    NA_VALUES,
    configure_na_values,
    normalize_column_value,
)


@pytest.fixture(autouse=True)
def restore_default_na_values():
    yield
    configure_na_values(DEFAULT_NA_VALUES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    add_na_values_args(parser)
    return parser


def test_inline_flag_configures_module_set_at_parse_time():
    build_parser().parse_args(["--na-values", "no observado\ndesconocido"])

    assert NA_VALUES == {"no observado", "desconocido"}
    assert normalize_column_value("No Observado") == ""
    assert normalize_column_value("none") == "none"


def test_path_flag_reads_file_at_parse_time(tmp_path):
    expressions_file = tmp_path / "expressions.txt"
    expressions_file.write_text("none\nno observado\n", encoding="utf-8")

    build_parser().parse_args(["--na-values-path", str(expressions_file)])

    assert NA_VALUES == {"none", "no observado"}


def test_no_flag_leaves_defaults_intact():
    build_parser().parse_args([])

    assert normalize_column_value("none") == ""
    assert normalize_column_value("n/a") == ""
