# pyright: reportCallIssue=false
import json
from pathlib import Path

import pytest

from paper2pipeline.__main__ import main, parse_args
from paper2pipeline.pipeline import (
    ExtractConfig,
    ExtractRun,
    GatherConfig,
    MergeConfig,
    NormalizeConfig,
    Pipeline,
    load_pipeline,
)
from paper2table import __version__


def test_version_prints_version_string(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--version"])
    assert f"paper2pipeline {__version__}" in capsys.readouterr().out


def test_load_pipeline_minimal(tmp_path):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(
        json.dumps({"input_paths": ["papers"], "output_path": "out"})
    )
    pipeline = load_pipeline(str(pipeline_file))
    assert pipeline.input_paths == ["papers"]
    assert pipeline.output_path == "out"
    assert pipeline.schema_path is None
    assert pipeline.normalize is None
    assert pipeline.extract is None
    assert pipeline.merge is None
    assert pipeline.gather is None


def test_load_pipeline_full():
    demo_pipeline = Path(__file__).parent / "data" / "demo.pipeline.json"
    pipeline = load_pipeline(str(demo_pipeline))

    assert pipeline.input_paths == ["tablas"]
    assert pipeline.schema_path == "schema.txt"
    assert pipeline.normalize == NormalizeConfig(interactive=False, inplace=True)
    assert pipeline.extract == ExtractConfig(
        runs=[
            ExtractRun(
                reader="agent", model="google-gla:gemini-2.5-flash", model_sleep=10
            )
        ],
        stats=True,
        validate=True,
        export=["csv", "html"],
    )
    assert pipeline.merge == MergeConfig(
        agreement_method="distinct-readers",
        jaccard_column_alignment=True,
        semantic_language="es",
        stats=True,
        export=["html"],
    )
    assert pipeline.gather == GatherConfig(
        convergence="rows",
        key_columns=["species", "family"],
        stats=True,
        export=["csv"],
    )


def test_normalize_defaults():
    config = NormalizeConfig()
    assert config.interactive is True
    assert config.inplace is False


def test_extract_run_defaults():
    run = ExtractRun()
    assert run.reader == "pdfplumber"
    assert run.verbose is False
    assert run.hybrid is False
    assert run.model is None


def test_merge_config_filter_semantic_columns():
    config = MergeConfig()
    assert config.filter_semantic_columns is False


def test_gather_config_defaults():
    config = GatherConfig()
    assert config.convergence == "none"
    assert config.key_columns is None
    assert config.stats is False
    assert config.export == []


def test_validate_only_prints_valid(tmp_path, capsys):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(
        json.dumps({"input_paths": ["papers"], "output_path": "out"})
    )
    main(["--validate-only", str(pipeline_file)])
    assert capsys.readouterr().out == "Pipeline is valid.\n"


def test_merge_config_hints_alignment_requires_hints():
    with pytest.raises(Exception):
        MergeConfig(hints_column_alignment="safe")


def test_merge_config_hints_alignment_accepts_inline_hints():
    config = MergeConfig(
        hints_column_alignment="safe", column_names_hints="species family"
    )
    assert config.hints_column_alignment == "safe"


def test_merge_config_hints_alignment_accepts_hints_path():
    config = MergeConfig(
        hints_column_alignment="unsafe", column_names_hints_path="hints.txt"
    )
    assert config.hints_column_alignment == "unsafe"


def test_merge_order_schema_columns_requires_schema_path():
    with pytest.raises(Exception):
        Pipeline(
            input_paths=["x"],
            output_path="y",
            merge=MergeConfig(order_schema_columns=True),
        )


def test_gather_order_schema_columns_requires_schema_path():
    with pytest.raises(Exception):
        Pipeline(
            input_paths=["x"],
            output_path="y",
            gather=GatherConfig(order_schema_columns=True),
        )


def test_order_schema_columns_accepted_with_schema_path():
    pipeline = Pipeline(
        input_paths=["x"],
        output_path="y",
        schema_path="schema.txt",
        merge=MergeConfig(order_schema_columns=True),
        gather=GatherConfig(order_schema_columns=True),
    )
    assert pipeline.merge.order_schema_columns is True
    assert pipeline.gather.order_schema_columns is True


def test_merge_coerce_schema_column_types_requires_schema_path():
    with pytest.raises(Exception):
        Pipeline(
            input_paths=["x"],
            output_path="y",
            merge=MergeConfig(coerce_schema_column_types=True),
        )


def test_gather_coerce_schema_column_types_requires_schema_path():
    with pytest.raises(Exception):
        Pipeline(
            input_paths=["x"],
            output_path="y",
            gather=GatherConfig(coerce_schema_column_types=True),
        )


def test_coerce_schema_column_types_accepted_with_schema_path():
    pipeline = Pipeline(
        input_paths=["x"],
        output_path="y",
        schema_path="schema.txt",
        merge=MergeConfig(coerce_schema_column_types=True),
        gather=GatherConfig(coerce_schema_column_types=True),
    )
    assert pipeline.merge.coerce_schema_column_types is True
    assert pipeline.gather.coerce_schema_column_types is True


def test_pipeline_rejects_unknown_fields(tmp_path):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(
        json.dumps({"input_paths": ["x"], "output_path": "y", "typo_field": True})
    )
    with pytest.raises(Exception):
        load_pipeline(str(pipeline_file))
