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
    "You are going to read the given paper and extract a table that corresponds to the given structure"
)

def call_agent(path):
    paper_path = Path(path)
    model = GoogleModel("gemini-1.5-flash")
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
