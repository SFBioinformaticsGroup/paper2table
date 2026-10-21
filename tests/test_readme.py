from pathlib import Path

from paper2pipeline.pipeline import (
    ExtractConfig,
    ExtractRun,
    GatherConfig,
    MergeConfig,
    Pipeline,
    ReadmeConfig,
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


def tables_json(citation: str | None = None) -> str:
    citation_value = f'"{citation}"' if citation is not None else "null"
    return f'{{"tables": [], "citation": {citation_value}}}'


def test_readme_config_override_defaults_to_false():
    assert ReadmeConfig().override is False


def test_pipeline_readme_defaults_to_none():
    assert Pipeline(working_path="x").readme is None


def test_pipeline_accepts_readme_config():
    pipeline = Pipeline(working_path="x", readme=ReadmeConfig(override=True))
    assert pipeline.readme.override is True


def test_parse_schema_columns_extracts_name_and_type(tmp_path):
    schema_file = tmp_path / "schema.txt"
    schema_file.write_text("familia:str\nnombre_cientifico:scientific_name\n", encoding="utf-8")
    assert parse_schema_columns(str(schema_file)) == [
        ("familia", "str"),
        ("nombre_cientifico", "scientific_name"),
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
    tables_file.write_text(
        tables_json("Doe, J. (2023). Title. DOI: 10.1/2"), encoding="utf-8"
    )
    assert read_tables_json_citation(tables_file) == "Doe, J. (2023). Title. DOI: 10.1/2"


def test_read_tables_json_citation_returns_placeholder_when_absent(tmp_path):
    tables_file = tmp_path / "paper.tables.json"
    tables_file.write_text(tables_json(), encoding="utf-8")
    assert read_tables_json_citation(tables_file) == "[...]"


def test_list_paper_citations_reads_merges_directory(tmp_path):
    merges_dir = tmp_path / "merges"
    merges_dir.mkdir()
    (merges_dir / "smith2020.tables.json").write_text(
        tables_json("Smith, A. (2020). A study. https://doi.org/10.1/smith"),
        encoding="utf-8",
    )
    (merges_dir / "jones2021.tables.json").write_text(
        tables_json("Jones, B. (2021). Another study. https://doi.org/10.1/jones"),
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
        tables_json("Smith, A. (2020). A study. https://doi.org/10.1/smith"),
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
