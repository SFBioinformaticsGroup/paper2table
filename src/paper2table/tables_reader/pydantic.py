from pydantic import BaseModel

from . import TableReader


class TablesModelWrapper:
    """Wrapper for a TablesModel"""

    def __init__(self, model: BaseModel):
        self.model = model

    @property
    def tables(self) -> list[TableReader]:
        return self.model.tables

    def to_dict(self) -> str:
        return self.model.model_dump()
