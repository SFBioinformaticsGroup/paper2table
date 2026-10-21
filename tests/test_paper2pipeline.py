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
    ReadmeConfig,
    load_pipeline,
)
from paper2pipeline.readme import (
    generate_readme,
    list_paper_citations,
    list_tools,
    load_column_aliases,
    parse_aliases,
    parse_schema_columns,
    read_tables_json_citation,
    write_readme,
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


def test_readme_config_override_defaults_to_false():
    assert ReadmeConfig().override is False


def test_pipeline_readme_defaults_to_none():
    assert Pipeline(working_path="x").readme is None


def test_pipeline_accepts_readme_config():
    pipeline = Pipeline(working_path="x", readme=ReadmeConfig(override=True))
    assert pipeline.readme.override is True


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


def test_parse_schema_columns_extracts_name_and_type(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("familia:str\nnombre_cientifico:scientific_name\n", encoding="utf-8")
    assert parse_schema_columns(str(schema_file)) == [
        ("familia", "str"),
        ("nombre_cientifico", "scientific_name"),
    ]


def test_parse_schema_columns_handles_name_without_type(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("familia\nnombre_popular\n", encoding="utf-8")
    assert parse_schema_columns(str(schema_file)) == [
        ("familia", ""),
        ("nombre_popular", ""),
    ]


def test_parse_schema_columns_skips_blank_lines(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("familia:str\n\nnombre_popular:str\n", encoding="utf-8")
    assert parse_schema_columns(str(schema_file)) == [
        ("familia", "str"),
        ("nombre_popular", "str"),
    ]


def test_list_tools_always_includes_paper2table():
    pipeline = Pipeline(working_path="x")
    tools = list_tools(pipeline)
    assert any(t.startswith("paper2table") for t in tools)


def test_list_tools_includes_pdfplumber_when_used():
    pipeline = Pipeline(
        working_path="x",
        extract=ExtractConfig(runs=[ExtractRun(reader="pdfplumber")]),
    )
    tools = list_tools(pipeline)
    assert any(t.startswith("pdfplumber") for t in tools)


def test_list_tools_includes_model_when_agent_reader_used():
    pipeline = Pipeline(
        working_path="x",
        extract=ExtractConfig(
            runs=[ExtractRun(reader="agent", model="google-gla:gemini-2.5-flash")]
        ),
    )
    tools = list_tools(pipeline)
    assert "google-gla:gemini-2.5-flash" in tools


def test_list_tools_deduplicates_model_across_runs():
    pipeline = Pipeline(
        working_path="x",
        extract=ExtractConfig(
            runs=[
                ExtractRun(reader="agent", model="google-gla:gemini-2.5-flash"),
                ExtractRun(reader="agent", model="google-gla:gemini-2.5-flash"),
            ]
        ),
    )
    tools = list_tools(pipeline)
    assert tools.count("google-gla:gemini-2.5-flash") == 1


def test_list_tools_includes_spacy_when_semantic_alignment_enabled():
    pipeline = Pipeline(
        working_path="x",
        merge=MergeConfig(column_name_semantic_alignment=True),
    )
    tools = list_tools(pipeline)
    assert any(t.startswith("spacy") for t in tools)


def test_list_tools_omits_spacy_when_no_semantic_alignment():
    pipeline = Pipeline(working_path="x", merge=MergeConfig())
    tools = list_tools(pipeline)
    assert not any(t.startswith("spacy") for t in tools)


def test_parse_aliases_parses_colon_separated_pairs():
    assert parse_aliases("familia:family\nespecie:species\n") == {
        "familia": "family",
        "especie": "species",
    }


def test_parse_aliases_skips_blank_lines():
    assert parse_aliases("familia:family\n\nespecie:species\n") == {
        "familia": "family",
        "especie": "species",
    }


def test_load_column_aliases_reads_inline_merge_aliases(tmp_path):
    pipeline = Pipeline(
        working_path=str(tmp_path),
        merge=MergeConfig(column_aliases="familia:family\nespecie:species"),
    )
    assert load_column_aliases(pipeline) == {"familia": "family", "especie": "species"}


def test_load_column_aliases_reads_aliases_file_in_working_path(tmp_path):
    (tmp_path / "column_aliases.txt").write_text("familia:family\n", encoding="utf-8")
    pipeline = Pipeline(working_path=str(tmp_path))
    assert load_column_aliases(pipeline) == {"familia": "family"}


def test_load_column_aliases_returns_empty_when_no_aliases(tmp_path):
    pipeline = Pipeline(working_path=str(tmp_path))
    assert load_column_aliases(pipeline) == {}


def test_load_column_aliases_inline_takes_precedence_over_file(tmp_path):
    (tmp_path / "column_aliases.txt").write_text("other:family\n", encoding="utf-8")
    pipeline = Pipeline(
        working_path=str(tmp_path),
        merge=MergeConfig(column_aliases="familia:family"),
    )
    assert load_column_aliases(pipeline) == {"familia": "family"}


def test_read_tables_json_citation_reads_string_citation(tmp_path):
    tables_file = tmp_path / "paper.tables.json"
    tables_file.write_text('{"citation": "Doe, J. (2023). Title. DOI: 10.1/2"}', encoding="utf-8")
    assert read_tables_json_citation(tables_file) == "Doe, J. (2023). Title. DOI: 10.1/2"


def test_read_tables_json_citation_returns_placeholder_when_absent(tmp_path):
    tables_file = tmp_path / "paper.tables.json"
    tables_file.write_text("{}", encoding="utf-8")
    assert read_tables_json_citation(tables_file) == "[...]"


def test_list_paper_citations_reads_merges_directory(tmp_path):
    merges_dir = tmp_path / "merges"
    merges_dir.mkdir()
    (merges_dir / "smith2020.tables.json").write_text(
        '{"citation": "Smith, A. (2020). A study. https://doi.org/10.1/smith"}',
        encoding="utf-8",
    )
    (merges_dir / "jones2021.tables.json").write_text(
        '{"citation": "Jones, B. (2021). Another study. https://doi.org/10.1/jones"}',
        encoding="utf-8",
    )
    (merges_dir / "tables.metadata.json").write_text("{}", encoding="utf-8")
    assert list_paper_citations(str(tmp_path)) == [
        ("jones2021", "Jones, B. (2021). Another study. https://doi.org/10.1/jones"),
        ("smith2020", "Smith, A. (2020). A study. https://doi.org/10.1/smith"),
    ]


def test_list_paper_citations_excludes_metadata_file(tmp_path):
    merges_dir = tmp_path / "merges"
    merges_dir.mkdir()
    (merges_dir / "tables.metadata.json").write_text("{}", encoding="utf-8")
    assert list_paper_citations(str(tmp_path)) == []


def test_list_paper_citations_falls_back_to_papers_directory(tmp_path):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    (papers_dir / "alpha.pdf").write_bytes(b"")
    (papers_dir / "beta.pdf").write_bytes(b"")
    assert list_paper_citations(str(tmp_path)) == [("alpha", "[...]"), ("beta", "[...]")]


def test_list_paper_citations_returns_empty_when_nothing_present(tmp_path):
    assert list_paper_citations(str(tmp_path)) == []


def test_generate_readme_contains_required_sections(tmp_path):
    pipeline = Pipeline(working_path=str(tmp_path))
    readme = generate_readme(pipeline, None)
    assert "## Goal and question" in readme
    assert "## Papers used" in readme
    assert "## Tools and version" in readme
    assert "## Data model" in readme
    assert "## Results" in readme
    assert "## Curation" in readme


def test_generate_readme_fills_schema_columns(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("familia:str\nnombre_cientifico:scientific_name\n", encoding="utf-8")
    pipeline = Pipeline(working_path=str(tmp_path))
    readme = generate_readme(pipeline, str(schema_file))
    assert "| familia | [...] | text | [...] |  | [...] |" in readme
    assert "| nombre_cientifico | [...] | text | [...] |  | [...] |" in readme


def test_generate_readme_maps_int_type_to_number(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("count:int\n", encoding="utf-8")
    pipeline = Pipeline(working_path=str(tmp_path))
    readme = generate_readme(pipeline, str(schema_file))
    assert "| count | [...] | number | [...] |  | [...] |" in readme


def test_generate_readme_fills_alternative_names_from_aliases(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("family:str\nspecies:str\n", encoding="utf-8")
    pipeline = Pipeline(
        working_path=str(tmp_path),
        merge=MergeConfig(column_aliases="familia:family\nespecie:species"),
    )
    readme = generate_readme(pipeline, str(schema_file))
    assert "| family | [...] | text | [...] | familia | [...] |" in readme
    assert "| species | [...] | text | [...] | especie | [...] |" in readme


def test_generate_readme_fills_papers_from_merges(tmp_path):
    merges_dir = tmp_path / "merges"
    merges_dir.mkdir()
    (merges_dir / "smith2020.tables.json").write_text(
        '{"citation": "Smith, A. (2020). A study. https://doi.org/10.1/smith"}',
        encoding="utf-8",
    )
    pipeline = Pipeline(working_path=str(tmp_path))
    readme = generate_readme(pipeline, None)
    assert "| smith2020 | Smith, A. (2020). A study. https://doi.org/10.1/smith | [...] |" in readme


def test_generate_readme_files_section_uses_gather_csv_when_configured(tmp_path):
    pipeline = Pipeline(
        working_path=str(tmp_path),
        gather=GatherConfig(export=["csv"]),
    )
    readme = generate_readme(pipeline, None)
    assert "`gathers/csv/`" in readme


def test_generate_readme_files_section_uses_merges_csv_when_no_gather(tmp_path):
    pipeline = Pipeline(
        working_path=str(tmp_path),
        merge=MergeConfig(export=["csv"]),
    )
    readme = generate_readme(pipeline, None)
    assert "`merges/csv/`" in readme


def test_write_readme_creates_file(tmp_path):
    pipeline = Pipeline(working_path=str(tmp_path))
    write_readme(pipeline, None)
    assert (tmp_path / "README.md").exists()


def test_write_readme_does_not_overwrite_existing_file(tmp_path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("custom content", encoding="utf-8")
    pipeline = Pipeline(working_path=str(tmp_path))
    write_readme(pipeline, None)
    assert readme_path.read_text(encoding="utf-8") == "custom content"


def test_write_readme_override_replaces_existing_file(tmp_path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("custom content", encoding="utf-8")
    pipeline = Pipeline(working_path=str(tmp_path))
    write_readme(pipeline, None, override=True)
    assert readme_path.read_text(encoding="utf-8") != "custom content"
    assert "## Data model" in readme_path.read_text(encoding="utf-8")
