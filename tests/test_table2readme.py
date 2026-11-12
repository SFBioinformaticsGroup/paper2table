import json
from pathlib import Path

from paper2pipeline.pipeline import Pipeline, ReadmeConfig
from table2readme.generator import (
    add_reader_tool,
    generate_readme,
    list_paper_citations,
    list_tools,
    load_column_aliases,
    parse_aliases,
    parse_schema_columns,
    read_tables_json_citation,
    write_readme,
)


def tables_json(citation: str | None = None) -> str:
    citation_value = f'"{citation}"' if citation is not None else "null"
    return f'{{"tables": [], "citation": {citation_value}}}'


def write_run_metadata(tables_dir: Path, run_id: str, reader: str) -> None:
    run_dir = tables_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "tables.metadata.json").write_text(
        json.dumps({"reader": reader, "id": run_id, "datetime": "2026-01-01T00:00:00"}),
        encoding="utf-8",
    )


def test_readme_config_override_defaults_to_false():
    assert ReadmeConfig().override is False


def test_pipeline_readme_defaults_to_none():
    assert Pipeline(working_path="x").readme is None


def test_pipeline_accepts_readme_config():
    pipeline = Pipeline(working_path="x", readme=ReadmeConfig(override=True))
    assert pipeline.readme is not None
    assert pipeline.readme.override is True


def test_parse_schema_columns_extracts_name_and_type():
    content = "familia:str\nnombre_cientifico:scientific_name\n"
    assert parse_schema_columns(content) == [
        ("familia", "str"),
        ("nombre_cientifico", "scientific_name"),
    ]


def test_parse_schema_columns_skips_blank_lines():
    content = "familia:str\n\nnombre_popular:str\n"
    assert parse_schema_columns(content) == [
        ("familia", "str"),
        ("nombre_popular", "str"),
    ]


def test_list_tools_always_includes_paper2table_and_spacy():
    tools = list_tools(None)
    assert any(tool.startswith("paper2table") for tool in tools)
    assert any(tool.startswith("spacy") for tool in tools)


def test_list_tools_reads_reader_from_tables_metadata(tmp_path):
    write_run_metadata(tmp_path, "run1", "pdfplumber")
    tools = list_tools(tmp_path)
    assert any(tool.startswith("pdfplumber") for tool in tools)


def test_list_tools_reads_agent_model_from_tables_metadata(tmp_path):
    write_run_metadata(tmp_path, "gemini", "google-gla:gemini-2.5-flash")
    tools = list_tools(tmp_path)
    assert "google-gla:gemini-2.5-flash" in tools


def test_list_tools_parses_hybrid_reader_as_reader_plus_model(tmp_path):
    write_run_metadata(
        tmp_path, "pymupdf-hybrid", "hybrid-pymupdf-google-gla:gemini-2.5-flash"
    )
    tools = list_tools(tmp_path)
    assert any(tool.startswith("pymupdf") for tool in tools)
    assert "google-gla:gemini-2.5-flash" in tools


def test_list_tools_deduplicates_across_runs(tmp_path):
    write_run_metadata(tmp_path, "run1", "google-gla:gemini-2.5-flash")
    write_run_metadata(tmp_path, "run2", "google-gla:gemini-2.5-flash")
    tools = list_tools(tmp_path)
    assert tools.count("google-gla:gemini-2.5-flash") == 1


def test_add_reader_tool_handles_plain_reader():
    tools: list[str] = []
    seen_readers: set[str] = set()
    seen_models: set[str] = set()
    add_reader_tool("pdfplumber", tools, seen_readers, seen_models)
    assert len(tools) == 1
    assert tools[0].startswith("pdfplumber")


def test_add_reader_tool_handles_unknown_bare_reader():
    tools: list[str] = []
    add_reader_tool("tablemerge", tools, set(), set())
    assert tools == ["tablemerge"]


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


def test_load_column_aliases_reads_inline():
    assert load_column_aliases("familia:family\nespecie:species", None) == {
        "familia": "family",
        "especie": "species",
    }


def test_load_column_aliases_reads_from_path(tmp_path):
    aliases_file = tmp_path / "aliases.txt"
    aliases_file.write_text("familia:family\n", encoding="utf-8")
    assert load_column_aliases(None, str(aliases_file)) == {"familia": "family"}


def test_load_column_aliases_returns_empty_when_neither_given():
    assert load_column_aliases(None, None) == {}


def test_load_column_aliases_inline_takes_precedence_over_path(tmp_path):
    aliases_file = tmp_path / "aliases.txt"
    aliases_file.write_text("other:family\n", encoding="utf-8")
    assert load_column_aliases("familia:family", str(aliases_file)) == {
        "familia": "family"
    }


def test_read_tables_json_citation_reads_string_citation(tmp_path):
    tables_file = tmp_path / "paper.tables.json"
    tables_file.write_text(
        tables_json("Doe, J. (2023). Title. DOI: 10.1/2"), encoding="utf-8"
    )
    assert read_tables_json_citation(tables_file) == "Doe, J. (2023). Title. DOI: 10.1/2"


def test_read_tables_json_citation_returns_placeholder_when_absent(tmp_path):
    tables_file = tmp_path / "paper.tables.json"
    tables_file.write_text(tables_json(), encoding="utf-8")
    assert read_tables_json_citation(tables_file) == "[...]"


def test_list_paper_citations_reads_merges_directory(tmp_path):
    (tmp_path / "smith2020.tables.json").write_text(
        tables_json("Smith, A. (2020). A study. https://doi.org/10.1/smith"),
        encoding="utf-8",
    )
    (tmp_path / "jones2021.tables.json").write_text(
        tables_json("Jones, B. (2021). Another study. https://doi.org/10.1/jones"),
        encoding="utf-8",
    )
    (tmp_path / "tables.metadata.json").write_text("{}", encoding="utf-8")
    assert list_paper_citations(tmp_path) == [
        ("jones2021", "Jones, B. (2021). Another study. https://doi.org/10.1/jones"),
        ("smith2020", "Smith, A. (2020). A study. https://doi.org/10.1/smith"),
    ]


def test_list_paper_citations_excludes_metadata_file(tmp_path):
    (tmp_path / "tables.metadata.json").write_text("{}", encoding="utf-8")
    assert list_paper_citations(tmp_path) == []


def test_list_paper_citations_returns_empty_when_merges_path_is_none():
    assert list_paper_citations(None) == []


def test_generate_readme_contains_required_sections():
    readme = generate_readme(None, None, None, None, {})
    assert "## Goal and question" in readme
    assert "## Papers used" in readme
    assert "## Tools and version" in readme
    assert "## Data model" in readme
    assert "## Results" in readme
    assert "## Curation" in readme


def test_generate_readme_fills_schema_columns():
    schema_content = "familia:str\nnombre_cientifico:scientific_name\n"
    readme = generate_readme(None, None, None, schema_content, {})
    assert "| familia | [...] | text | [...] |  | [...] |" in readme
    assert "| nombre_cientifico | [...] | text | [...] |  | [...] |" in readme


def test_generate_readme_maps_int_type_to_number():
    readme = generate_readme(None, None, None, "count:int\n", {})
    assert "| count | [...] | number | [...] |  | [...] |" in readme


def test_generate_readme_fills_alternative_names_from_aliases():
    schema_content = "family:str\nspecies:str\n"
    aliases = {"familia": "family", "especie": "species"}
    readme = generate_readme(None, None, None, schema_content, aliases)
    assert "| family | [...] | text | [...] | familia | [...] |" in readme
    assert "| species | [...] | text | [...] | especie | [...] |" in readme


def test_generate_readme_fills_papers_from_merges_path(tmp_path):
    (tmp_path / "smith2020.tables.json").write_text(
        tables_json("Smith, A. (2020). A study. https://doi.org/10.1/smith"),
        encoding="utf-8",
    )
    readme = generate_readme(tmp_path, None, None, None, {})
    assert "| smith2020 | Smith, A. (2020). A study. https://doi.org/10.1/smith | [...] |" in readme


def test_generate_readme_files_section_uses_gathers_csv_when_present(tmp_path):
    (tmp_path / "csv").mkdir()
    readme = generate_readme(None, None, tmp_path, None, {})
    assert "`gathers/csv/`" in readme


def test_generate_readme_files_section_uses_merges_csv_when_no_gathers(tmp_path):
    (tmp_path / "csv").mkdir()
    readme = generate_readme(tmp_path, None, None, None, {})
    assert "`merges/csv/`" in readme


def test_generate_readme_files_section_uses_tables_csv_when_no_merges_or_gathers(tmp_path):
    (tmp_path / "run1" / "csv").mkdir(parents=True)
    readme = generate_readme(None, tmp_path, None, None, {})
    assert "`tables/<run-id>/csv/`" in readme


def test_generate_readme_files_section_omits_all_variants_when_no_paths_given():
    readme = generate_readme(None, None, None, None, {})
    assert "`gathers/csv/`" not in readme
    assert "`merges/csv/`" not in readme
    assert "`tables/<run-id>/csv/`" not in readme
    assert "- `[path/to/curated.csv]`" in readme


def test_write_readme_creates_file(tmp_path):
    output_path = tmp_path / "README.md"
    assert write_readme(output_path, None, None, None, None, {}, override=False) is True
    assert output_path.exists()


def test_write_readme_does_not_overwrite_existing_file(tmp_path):
    output_path = tmp_path / "README.md"
    output_path.write_text("custom content", encoding="utf-8")
    assert write_readme(output_path, None, None, None, None, {}, override=False) is False
    assert output_path.read_text(encoding="utf-8") == "custom content"


def test_write_readme_override_replaces_existing_file(tmp_path):
    output_path = tmp_path / "README.md"
    output_path.write_text("custom content", encoding="utf-8")
    assert write_readme(output_path, None, None, None, None, {}, override=True) is True
    content = output_path.read_text(encoding="utf-8")
    assert content != "custom content"
    assert "## Data model" in content
