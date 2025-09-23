from pydantic import create_model
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from pathlib import Path
from pydantic_ai import Agent, BinaryContent

from typing import Any
from pydantic import create_model


from typing import Any
from pydantic import create_model


def parse_schema(schema_str: str) -> dict[str, tuple[Any, ...]]:
    """Parse schema string into a dictionary of field definitions."""
    normalized = schema_str.replace(",", " ").replace("\n", " ")
    parts = [p.strip() for p in normalized.split() if p.strip()]

    type_map: dict[str, Any] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
    }

    fields: dict[str, tuple[Any, ...]] = {}
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Invalid field specifier: {part}")
        name, type_str = part.split(":", 1)
        if type_str not in type_map:
            raise ValueError(f"Unsupported type: {type_str}")
        fields[name] = (type_map[type_str], ...)

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
    return create_model("TableModel", rows=(list[RowModel], ...))


instructions = (
    "You are a PhD researcher."
    "You are going to read the given paper and extract a table that corresponds to the given structure",
    "In order to generate the table, only consider data that is in tabular format. Ignore any plain text paragraph",
)


def call_agent(path, model, schema):
    paper_path = Path(path)
    agent = Agent(
        model,
        output_type=build_table_model(schema),
        instructions=instructions,
    )
    return agent.run_sync(
        [
            BinaryContent(data=paper_path.read_bytes(), media_type="application/pdf"),
        ]
    )
