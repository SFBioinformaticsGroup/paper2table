from pydantic import create_model
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from pathlib import Path
from pydantic_ai import Agent, BinaryContent

# TODO this will be generated dynamically
RowModel = create_model(
    "RowModel",
    common_name=(str, ...),
    scientific_name=(str, ...),
    species=(str, ...),
)

TableModel = create_model("TableModel", rows=(list[RowModel], ...))

instructions = (
    "You are a PhD researcher."
    "You are going to read the given paper and extract a table that corresponds to the given structure",
    "In order to generate the table, only consider data that is in tabular format. Ignore any plain text paragraph"
)

def call_agent(path, model):
    paper_path = Path(path)
    agent = Agent(
        model,
        output_type=TableModel,
        instructions=instructions,
    )
    return agent.run_sync(
        [
            BinaryContent(data=paper_path. read_bytes(), media_type="application/pdf"),
        ]
    )
