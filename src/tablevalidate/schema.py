from typing import List, Union, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class ValueWithAgreement(BaseModel):
    value: str
    agreement_level: int


ColumnValue = Union[str, List[ValueWithAgreement]]


class Row(BaseModel):
    agreement_level_: Optional[int] = Field(None)

    model_config = ConfigDict(extra="allow")

    def __getitem__(self, item: str) -> ColumnValue:
        return self.__dict__[item]

    def get_columns(self) -> Dict[str, ColumnValue]:
        return {k: v for k, v in self if k != "agreement_level_"}

    def get_agreement_level(self):
        return 1 if self.agreement_level_ is None else self.agreement_level_


class TableFragment(BaseModel):
    rows: List[Row]
    page: int


class TableWithRows(BaseModel):
    rows: List[Row]
    page: int


class TableWithFragments(BaseModel):
    table_fragments: List[TableFragment]


Table = Union[TableWithRows, TableWithFragments]


class Metadata(BaseModel):
    filename: Optional[str]

    model_config = ConfigDict(extra="allow")


Citation = Union[Optional[str], List[ValueWithAgreement]]


class TablesFile(BaseModel):
    tables: List[Table]
    citation: Citation
    metadata: Optional[Metadata] = None


def get_table_fragments(table: Table) -> list[TableFragment]:
    if hasattr(table, "rows") and table.rows:
        return [table]
    if hasattr(table, "table_fragments") and table.table_fragments:
        return table.table_fragments
    return []
