from pydantic import BaseModel

from . import TableReader


class TablesModelWrapper:
    """
    Wrapper for a TablesModel that
    satisfies TablesReader protocol
    """

    def __init__(self, model: BaseModel):
        self.model = model

    @property
    def tables(self) -> list[TableReader]:
        return self.model.tables  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def citation(self) -> str | None:
        return None

    def to_dict(self) -> dict:
        return self.model.model_dump()  # pyright: ignore[reportReturnType]
