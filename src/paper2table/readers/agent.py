from pathlib import Path
from typing import Any

from pydantic import BaseModel, create_model
from pydantic_ai import Agent, BinaryContent

from utils.tokenize_schema import tokenize_schema

from ..tables_protocol import TableProtocol, TablesProtocol

types_map: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def parse_schema(schema_str: str) -> dict[str, tuple[Any, ...]]:
    parts = tokenize_schema(schema_str)

    fields: dict[str, tuple[Any, ...]] = {}
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Invalid field specifier: {part}")
        name, type_str = part.split(":", 1)
        if type_str not in types_map:
            raise ValueError(f"Unsupported type: {type_str}")
        fields[name] = (types_map[type_str], ...)

    return fields


def build_table_model(schema: str):
    """
    Build and return a TableModel from a schema string.

    Schema string format examples:
        "common_name:str species:str"
        "name:str, age:int, alive:bool"
        "height:float\nweight:float"
    """
    fields = parse_schema(schema)
    RowModel = create_model("RowModel", **fields)
    return create_model("TableModel", rows=(list[RowModel], ...), page=(int, ...))


def build_tables_model(schema: str):
    return create_model(
        "TablesModel",
        tables=(list[build_table_model(schema)], ...),
        citation=(str, ...),
    )


instructions = (
    "CONTEXT",
    "=======",
    "You are a PhD researcher.",
    "",
    "TASK",
    "====",
    "You are going to read the given paper and extract zero or more tables that corresponds to the given structure",
    "",
    "RESTRICTIONS" "============",
    " * In order to generate the table, only consider data that is in tabular format. Ignore any plain text paragraph",
    " * Don't try to translate data. Keep it in its original language",
    " * Don't try to transform cell's contents nor to resume text nor to paraphrase it. Extract data as-is",
    " * If there is no data available for a column and a row, don't try to generate new data. Place an empty string instead",
    " * When possible, you'll generate in the citation output field an APA-style cite of the paper from where the table was extracted",
    " * Annotate each table with the page number in the paper where it starts",
)


class TableModelWrapper:
    """Wrapper for a TableModel"""

    def __init__(self, model: BaseModel):
        self.model = model

    def to_dict(self) -> str:
        return self.model.model_dump()


class TablesModelWrapper:
    """Wrapper for a TablesModel"""

    def __init__(self, model: BaseModel):
        self.model = model

    @property
    def tables(self) -> list[TableProtocol]:
        return self.model.tables

    def to_dict(self) -> str:
        return self.model.model_dump()


def read_tables(path: str, model: str, schema: str) -> TablesProtocol:
    paper_path = Path(path)
    agent = Agent(
        model,
        output_type=build_tables_model(schema),
        instructions=instructions,
    )
    return agent.run_sync(
        [
            BinaryContent(data=paper_path.read_bytes(), media_type="application/pdf"),
        ]
    ).output.model_dump()
