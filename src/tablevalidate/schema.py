from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator

from utils.column_values import normalize_column_value
from utils.str import normalize_str


ScalarValue = str | int | float | bool


class ValueWithAgreement(BaseModel):
    value: ScalarValue
    agreement_level: int


ColumnValue = None | ScalarValue | List[ValueWithAgreement]

CurationType = Literal["none", "automatic", "manual"]

_META_COLUMNS = frozenset(
    (
        "agreement_level_",
        "curation_type_",
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
    curation_type_: Optional[CurationType] = Field(None)

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

    def serialize_columns(self) -> Dict[str, str]:
        return {k: "\n".join(Row.to_texts(v)) for k, v in self.get_columns().items()}

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

    def get_curation_type(self):
        return "none" if self.curation_type_ is None else self.curation_type_

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

    def get_convergence_level(self, sources_count: int) -> Literal[0, 1, 2, 3, 4, 5]:
        """
        0 = sources/agreement mismatch
        1 = single source
        2 = multi-source with cell conflicts
        3 = multi-source convergent
        4 = automatic curation
        5 = manual curation
        """
        if self.get_curation_type() == "manual":
            return 5

        if self.get_curation_type() == "automatic":
            return 4

        if sources_count == self.get_agreement_level():
            if self.get_agreement_level() == 1:
                return 1

            if any(not Row.is_convergent(value) for value in self.get_column_values()):
                return 2

            return 3

        return 0

    def clone(
        self,
        agreement_level: Optional[int] = None,
        sources: Optional[List[str]] = None,
        row: Optional[int] = None,
        citation: Optional[str] = None,
        path: Optional[str] = None,
        page: Optional[int] = None,
        fragment: Optional[int] = None,
        curation_type: Optional[CurationType] = None,
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
            curation_type_=(
                curation_type if curation_type is not None else self.curation_type_
            ),
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

        return False

    @staticmethod
    def is_convergent(value: ColumnValue) -> bool:
        return not isinstance(value, list) or len(value) == 1

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
    def map_text(value: ColumnValue, fn: Callable[[str], ScalarValue]) -> ColumnValue:
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

    def get_convergent_rows(self, level: int = 1) -> List[Row]:
        sources_count = len(
            {source for row in self.rows for source in row.sources_ or []}
        )
        return [
            row
            for row in self.rows
            if row.get_convergence_level(sources_count) >= level
        ]


class Table(ABC):
    @abstractmethod
    def get_table_fragments(self) -> List[TableFragment]: ...

    @abstractmethod
    def is_empty(self) -> bool: ...

    def get_convergent_fragments(self, level: int = 1) -> List[TableFragment]:
        return [
            f
            for f in self.get_table_fragments()
            if len(f.get_convergent_rows(level)) == len(f.rows)
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

    def get_convergent_tables(self, level: int = 1) -> List[Table]:
        return [
            t
            for t in self.tables
            if len(t.get_convergent_fragments(level)) == len(t.get_table_fragments())
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
