from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator

from utils.column_values import normalize_column_value
from utils.str import normalize_str


ScalarValue = str | int | float | bool


class ValueWithAgreement(BaseModel):
    value: ScalarValue
    agreement_level: int


ColumnValue = None | ScalarValue | List[ValueWithAgreement]

_META_COLUMNS = frozenset(
    (
        "agreement_level_",
        "sources_",
        "row_",
        "citation_",
        "path_",
        "page_",
        "fragment_",
    )
)


class Row(BaseModel):
    agreement_level_: Optional[int] = Field(None)
    sources_: Optional[List[str]] = Field(None)
    row_: Optional[int] = Field(None)
    citation_: Optional[str] = Field(None)
    path_: Optional[str] = Field(None)
    page_: Optional[int] = Field(None)
    fragment_: Optional[int] = Field(None)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def coerce_extra_columns(self) -> "Row":
        if self.__pydantic_extra__:
            for key, value in self.__pydantic_extra__.items():
                if isinstance(value, list):
                    self.__pydantic_extra__[key] = [
                        (
                            ValueWithAgreement.model_validate(v)
                            if isinstance(v, dict)
                            else v
                        )
                        for v in value
                    ]
        return self

    def __getitem__(self, item: str) -> ColumnValue:
        return self.__dict__[item]

    def get_columns(self) -> Dict[str, ColumnValue]:
        return {k: v for k, v in self if k not in _META_COLUMNS}

    def get_column_values(self):
        return self.get_columns().values()

    def get_meta_columns(self) -> Dict[str, Any]:
        return {k: v for k, v in self if k in _META_COLUMNS}

    @staticmethod
    def is_semantic_column(name: str) -> bool:
        try:
            float(name)
            return False
        except ValueError:
            return True

    def get_semantic_columns(self) -> Dict[str, ColumnValue]:
        return {
            k: v for k, v in self.get_columns().items() if self.is_semantic_column(k)
        }

    def is_empty(self) -> bool:
        return all(Row.is_empty_value(v) for v in self.get_column_values())

    def get_agreement_level(self):
        return 1 if self.agreement_level_ is None else self.agreement_level_

    def normalize(
        self,
        calculate_agreement: bool = False,
    ):
        return self.clone(
            columns={
                column: Row.normalize_value(value)
                for column, value in self.get_columns().items()
            },
            agreement_level=(
                self.get_agreement_level()
                if calculate_agreement
                else self.agreement_level_
            ),
        )

    def clone(
        self,
        agreement_level: Optional[int] = None,
        sources: Optional[List[str]] = None,
        row: Optional[int] = None,
        citation: Optional[str] = None,
        path: Optional[str] = None,
        page: Optional[int] = None,
        fragment: Optional[int] = None,
        columns: Optional[Dict[str, ColumnValue]] = None,
    ) -> "Row":
        return Row(
            agreement_level_=(
                agreement_level
                if agreement_level is not None
                else self.agreement_level_
            ),
            sources_=sources if sources is not None else self.sources_,
            row_=row if row is not None else self.row_,
            citation_=citation if citation is not None else self.citation_,
            path_=path if path is not None else self.path_,
            page_=page if page is not None else self.page_,
            fragment_=fragment if fragment is not None else self.fragment_,
            **(columns if columns is not None else self.get_columns()),
        )

    @staticmethod
    def column_names(rows: "List[Row]") -> "List[str]":
        return list(dict.fromkeys(col for row in rows for col in row.get_columns()))

    @staticmethod
    def is_empty_value(value: ColumnValue) -> bool:
        if value is None:
            return True

        if isinstance(value, list):
            return all(
                isinstance(v.value, str) and not normalize_column_value(v.value)
                for v in value
            )

        if isinstance(value, str):
            return not normalize_column_value(value)

        return False  # int, float, bool — never empty

    @staticmethod
    def is_convergent(value: ColumnValue) -> bool:
        if not isinstance(value, list):
            return True
        return len(value) == 1

    @staticmethod
    def normalize_value(value: ColumnValue) -> ColumnValue:
        if value is None:
            return None

        if isinstance(value, str):
            return normalize_column_value(value)

        if isinstance(value, list):
            return [
                ValueWithAgreement(
                    value=(
                        normalize_column_value(v.value)
                        if isinstance(v.value, str)
                        else v.value
                    ),
                    agreement_level=v.agreement_level,
                )
                for v in value
            ]

        return value

    @staticmethod
    def map_text(
        value: ColumnValue, fn: Callable[[str], ScalarValue]
    ) -> ColumnValue:
        """Transforms cell's string values"""
        if isinstance(value, str):
            return fn(value)
        if isinstance(value, list):
            return [
                ValueWithAgreement(
                    value=fn(v.value) if isinstance(v.value, str) else v.value,
                    agreement_level=v.agreement_level,
                )
                for v in value
            ]
        return value

    @staticmethod
    def to_text(value: ColumnValue) -> str:
        """Transforms cell's value to string"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return str(value[0].value) if value else ""
        return str(value)

    @staticmethod
    def to_texts(value: ColumnValue) -> List[str]:
        """Transforms cell's value to list of strings"""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(entry.value) for entry in value]
        return [str(value)]

    @staticmethod
    def to_multivalued(value: ColumnValue) -> List[ValueWithAgreement]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [ValueWithAgreement(value=value, agreement_level=1)]


class TableFragment(BaseModel):
    rows: List[Row]
    page: int
    _groups: Optional[Dict[int, List[Row]]] = PrivateAttr(default=None)

    def get_column_names(self) -> List[str]:
        return Row.column_names(self.rows)

    def columns_count(self) -> int:
        return len(self.get_column_names())

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)

    def get_convergent_rows(self) -> List[Row]:
        """Return rows that have a single unique value"""
        return [
            row
            for row in self.rows
            if all([Row.is_convergent(v) for v in row.get_column_values()])
        ]


class Table(ABC):
    @abstractmethod
    def get_table_fragments(self) -> List[TableFragment]: ...

    @abstractmethod
    def is_empty(self) -> bool: ...

    def get_convergent_fragments(self) -> List[TableFragment]:
        return [
            f
            for f in self.get_table_fragments()
            if len(f.get_convergent_rows()) == len(f.rows)
        ]


class TableWithRows(BaseModel, Table):
    rows: List[Row]
    page: int

    def get_table_fragments(self) -> List[TableFragment]:
        return [TableFragment(rows=self.rows, page=self.page)]

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)


class TableWithFragments(BaseModel, Table):
    table_fragments: List[TableFragment]

    def get_table_fragments(self) -> List[TableFragment]:
        return list(self.table_fragments)

    def is_empty(self) -> bool:
        return all(fragment.is_empty() for fragment in self.table_fragments)


class Curation(BaseModel):
    curator: str
    description: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Metadata(BaseModel):
    filename: Optional[str]
    curations: Optional[List["Curation"]] = None

    model_config = ConfigDict(extra="allow")


Citation = None | str | List[ValueWithAgreement]


class TablesFile(BaseModel):
    tables: List[TableWithRows | TableWithFragments]
    citation: Citation
    metadata: Optional[Metadata] = None
    uuid: Optional[str] = None

    def has_curations(self) -> bool:
        return bool(self.metadata and self.metadata.curations)

    def get_convergent_tables(self) -> List[Table]:
        return [
            t
            for t in self.tables
            if len(t.get_convergent_fragments()) == len(t.get_table_fragments())
        ]

    def clone(
        self,
        tables: Optional[List[TableWithRows | TableWithFragments]] = None,
        citation: Optional[Citation] = None,
        metadata: Optional[Metadata] = None,
        uuid: Optional[str] = None,
    ) -> "TablesFile":
        return TablesFile(
            tables=tables if tables is not None else self.tables,
            citation=citation if citation is not None else self.citation,
            metadata=metadata if metadata is not None else self.metadata,
            uuid=uuid if uuid is not None else self.uuid,
        )

    @staticmethod
    def normalize_citation(citation: Citation) -> Citation:
        if citation is None:
            return None
        if isinstance(citation, str):
            return normalize_str(citation)
        return [
            ValueWithAgreement(
                value=normalize_str(v.value) if isinstance(v.value, str) else v.value,
                agreement_level=v.agreement_level,
            )
            for v in citation
        ]
