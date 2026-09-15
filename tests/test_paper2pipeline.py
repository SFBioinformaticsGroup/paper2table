import pytest

from paper2pipeline.__main__ import parse_args
from paper2table import __version__


def test_version_prints_version_string(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--version"])
    assert f"paper2pipeline {__version__}" in capsys.readouterr().out
