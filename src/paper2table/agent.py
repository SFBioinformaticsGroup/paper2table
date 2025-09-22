from pydantic import create_model
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic import BaseModel, Field


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

def call_agent():
    model = GoogleModel("gemini-1.5-flash")
    agent = Agent(
        model,
        output_type=TableModel,
        instructions=instructions,
    )
    return agent.run_sync(
        """
    | common_name        | scientific_name         | species       |
    |--------------------|-------------------------|---------------|
    | Sunflower          | Helianthus annuus       | annuus        |
    | Rose               | Rosa gallica            | gallica       |
    | Tulip              | Tulipa gesneriana       | gesneriana    |
    | Lavender           | Lavandula angustifolia  | angustifolia  |
    | Oak                | Quercus robur           | robur         |
    | Maple              | Acer saccharum          | saccharum     |
    | Dandelion          | Taraxacum officinale    | officinale    |
    | Bamboo             | Bambusa vulgaris        | vulgaris      |
    | Cactus (Prickly Pear) | Opuntia ficus-indica | ficus-indica  |
    | Coffee             | Coffea arabica          | arabica       |
"""
    )
