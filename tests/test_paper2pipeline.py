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
from paper2pipeline.runner import build_extract_args, build_merge_args, find_schema_path
from paper2table import __version__


def test_version_prints_version_string(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--version"])
    assert f"paper2pipeline {__version__}" in capsys.readouterr().out


def test_load_pipeline_minimal(tmp_path):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(json.dumps({"working_path": "x"}))
    pipeline = load_pipeline(str(pipeline_file))
    assert pipeline.working_path == "x"
    assert pipeline.normalize is None
    assert pipeline.extract is None
    assert pipeline.merge is None
    assert pipeline.gather is None


def test_load_pipeline_full():
    demo_pipeline = Path(__file__).parent / "data" / "demo.pipeline.jsonc"
    pipeline = load_pipeline(str(demo_pipeline))

    assert pipeline.working_path == "."
    assert pipeline.normalize == NormalizeConfig(interactive=False)
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


def test_override_defaults_to_false():
    assert ExtractConfig(runs=[ExtractRun()]).override is False
    assert MergeConfig().override is False
    assert GatherConfig().override is False


def test_validate_only_prints_valid(tmp_path, capsys):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(json.dumps({"working_path": "x"}))
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


def test_agent_reader_accepted_with_inline_schema():
    pipeline = Pipeline(
        working_path="x",
        extract=ExtractConfig(runs=[ExtractRun(reader="agent", schema="species family")]),
    )
    assert pipeline.extract.runs[0].reader == "agent"


def test_pipeline_rejects_unknown_fields(tmp_path):
    pipeline_file = tmp_path / "pipeline.json"
    pipeline_file.write_text(
        json.dumps({"working_path": "x", "typo_field": True})
    )
    with pytest.raises(Exception):
        load_pipeline(str(pipeline_file))


def test_extract_run_override_mappings_default_is_false():
    assert ExtractRun().override_mappings is False


def test_build_extract_args_hybrid_includes_mappings_path(tmp_path):
    run = ExtractRun(hybrid=True)
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-M" in args
    mappings_index = args.index("-M")
    assert args[mappings_index + 1] == str(tmp_path / "mappings")


def test_build_extract_args_non_hybrid_omits_mappings_path(tmp_path):
    run = ExtractRun(hybrid=False)
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-M" not in args


def test_build_extract_args_override_mappings_passes_flag(tmp_path):
    run = ExtractRun(hybrid=True, override_mappings=True)
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-F" in args


def test_merge_config_row_similarity_threshold_default():
    assert MergeConfig().row_similarity_threshold == 0.6


def test_build_merge_args_row_similarity_threshold(tmp_path):
    config = MergeConfig(row_similarity_threshold=0.5)
    args = build_merge_args(config, tmp_path, None)
    assert "--row-similarity-threshold" in args
    threshold_index = args.index("--row-similarity-threshold")
    assert args[threshold_index + 1] == "0.5"


def test_build_merge_args_row_similarity_threshold_default_omitted(tmp_path):
    config = MergeConfig()
    args = build_merge_args(config, tmp_path, None)
    assert "--row-similarity-threshold" not in args


def test_find_schema_path_returns_none_when_missing(tmp_path):
    assert find_schema_path(tmp_path) is None


def test_find_schema_path_returns_none_when_empty(tmp_path):
    (tmp_path / "schema.txt").write_text("   \n", encoding="utf-8")
    assert find_schema_path(tmp_path) is None


def test_find_schema_path_returns_path_when_present(tmp_path):
    (tmp_path / "schema.txt").write_text("species family color\n", encoding="utf-8")
    assert find_schema_path(tmp_path) == str(tmp_path / "schema.txt")
