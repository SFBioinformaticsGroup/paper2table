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
from paper2pipeline.runner import apply_page_ranges, build_extract_args, build_merge_args, find_file
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


def test_merge_config_hints_alignment_accepts_inline_hints():
    config = MergeConfig(
        hints_column_alignment="safe", column_hints="species family"
    )
    assert config.hints_column_alignment == "safe"


def test_merge_config_hints_alignment_accepts_hints_path():
    config = MergeConfig(
        hints_column_alignment="unsafe", column_hints_path="hints.txt"
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


def test_find_file_returns_none_when_missing(tmp_path):
    assert find_file("schema.txt", tmp_path) is None


def test_find_file_returns_none_when_empty(tmp_path):
    (tmp_path / "schema.txt").write_text("   \n", encoding="utf-8")
    assert find_file("schema.txt", tmp_path) is None


def test_find_file_returns_path_when_present(tmp_path):
    (tmp_path / "schema.txt").write_text("species family color\n", encoding="utf-8")
    assert find_file("schema.txt", tmp_path) == str(tmp_path / "schema.txt")


def test_build_extract_args_uses_column_hints_txt_when_present(tmp_path):
    (tmp_path / "column_hints.txt").write_text("species\nfamily\n", encoding="utf-8")
    run = ExtractRun()
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-c" in args
    assert args[args.index("-c") + 1] == str(tmp_path / "column_hints.txt")


def test_build_extract_args_no_hints_when_nothing_present(tmp_path):
    run = ExtractRun()
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-c" not in args


def test_build_extract_args_explicit_hints_path_overrides_auto_detected(tmp_path):
    (tmp_path / "column_hints.txt").write_text("species\n", encoding="utf-8")
    run = ExtractRun(column_hints_path="/other/hints.txt")
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "-c" in args
    assert args[args.index("-c") + 1] == "/other/hints.txt"


def test_build_extract_args_inline_hints_passes_flag(tmp_path):
    run = ExtractRun(column_hints="species family")
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "--column-hints" in args
    assert args[args.index("--column-hints") + 1] == "species family"
    assert "-c" not in args


def test_build_extract_args_inline_hints_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_hints.txt").write_text("other\n", encoding="utf-8")
    run = ExtractRun(column_hints="species family")
    args = build_extract_args(run, None, tmp_path, ["paper.pdf"])
    assert "--column-hints" in args
    assert args[args.index("--column-hints") + 1] == "species family"
    assert "-c" not in args


def test_build_merge_args_uses_column_aliases_txt_when_present(tmp_path):
    (tmp_path / "column_aliases.txt").write_text("familia:family\n", encoding="utf-8")
    config = MergeConfig()
    args = build_merge_args(config, tmp_path, None)
    assert "--column-aliases-path" in args
    assert args[args.index("--column-aliases-path") + 1] == str(tmp_path / "column_aliases.txt")


def test_build_merge_args_inline_column_aliases_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_aliases.txt").write_text("familia:family\n", encoding="utf-8")
    config = MergeConfig(column_aliases="especie:species")
    args = build_merge_args(config, tmp_path, None)
    assert "--column-aliases" in args
    assert args[args.index("--column-aliases") + 1] == "especie:species"
    assert "--column-aliases-path" not in args


def test_build_merge_args_explicit_column_aliases_path_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_aliases.txt").write_text("familia:family\n", encoding="utf-8")
    config = MergeConfig(column_aliases_path="/other/aliases.txt")
    args = build_merge_args(config, tmp_path, None)
    assert "--column-aliases-path" in args
    assert args[args.index("--column-aliases-path") + 1] == "/other/aliases.txt"


def test_build_merge_args_uses_column_hints_txt_when_present(tmp_path):
    (tmp_path / "column_hints.txt").write_text("species\nfamily\n", encoding="utf-8")
    config = MergeConfig()
    args = build_merge_args(config, tmp_path, None)
    assert "--column-hints-path" in args
    assert args[args.index("--column-hints-path") + 1] == str(tmp_path / "column_hints.txt")


def test_build_merge_args_inline_column_hints_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_hints.txt").write_text("other\n", encoding="utf-8")
    config = MergeConfig(column_hints="species family")
    args = build_merge_args(config, tmp_path, None)
    assert "--column-hints" in args
    assert args[args.index("--column-hints") + 1] == "species family"
    assert "--column-hints-path" not in args


def test_build_merge_args_explicit_column_hints_path_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_hints.txt").write_text("other\n", encoding="utf-8")
    config = MergeConfig(column_hints_path="/other/hints.txt")
    args = build_merge_args(config, tmp_path, None)
    assert "--column-hints-path" in args
    assert args[args.index("--column-hints-path") + 1] == "/other/hints.txt"


def test_build_merge_args_uses_paper_aliases_txt_when_present(tmp_path):
    (tmp_path / "paper_aliases.txt").write_text("paperA:paperB\n", encoding="utf-8")
    config = MergeConfig()
    args = build_merge_args(config, tmp_path, None)
    assert "--paper-aliases-path" in args
    assert args[args.index("--paper-aliases-path") + 1] == str(tmp_path / "paper_aliases.txt")


def test_build_merge_args_inline_paper_aliases_takes_precedence_over_file(tmp_path):
    (tmp_path / "paper_aliases.txt").write_text("paperA:paperB\n", encoding="utf-8")
    config = MergeConfig(paper_aliases="paperX:paperY")
    args = build_merge_args(config, tmp_path, None)
    assert "--paper-aliases" in args
    assert args[args.index("--paper-aliases") + 1] == "paperX:paperY"
    assert "--paper-aliases-path" not in args


def test_build_merge_args_explicit_paper_aliases_path_takes_precedence_over_file(tmp_path):
    (tmp_path / "paper_aliases.txt").write_text("paperA:paperB\n", encoding="utf-8")
    config = MergeConfig(paper_aliases_path="/other/aliases.txt")
    args = build_merge_args(config, tmp_path, None)
    assert "--paper-aliases-path" in args
    assert args[args.index("--paper-aliases-path") + 1] == "/other/aliases.txt"


def test_extract_config_page_ranges_defaults_to_none():
    assert ExtractConfig(runs=[ExtractRun()]).page_ranges is None


def test_apply_page_ranges_appends_range_to_matching_file():
    result = apply_page_ranges(["/papers/alpha.pdf", "/papers/beta.pdf"], {"alpha": "5:10"})
    assert result == ["/papers/alpha.pdf:5:10", "/papers/beta.pdf"]


def test_apply_page_ranges_leaves_all_files_unchanged_when_no_match():
    result = apply_page_ranges(["/papers/alpha.pdf"], {"gamma": "1:3"})
    assert result == ["/papers/alpha.pdf"]


def test_apply_page_ranges_returns_original_list_when_none():
    result = apply_page_ranges(["/papers/alpha.pdf"], None)
    assert result == ["/papers/alpha.pdf"]
