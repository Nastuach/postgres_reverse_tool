from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any


class ConstraintType(Enum):
    PRIMARY_KEY = "PRIMARY KEY"
    FOREIGN_KEY = "FOREIGN KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT NULL"
    EXCLUSION = "EXCLUSION"


class TriggerEvent(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"


class TriggerTiming(Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD OF"


@dataclass
class Column:
    """Класс, представляющий колонку таблицы"""
    name: str
    data_type: str
    is_nullable: bool = True
    default_value: Optional[str] = None
    is_identity: bool = False
    character_max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    description: Optional[str] = None
    is_computed: bool = False
    computed_expression: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'data_type': self.data_type,
            'is_nullable': self.is_nullable,
            'default_value': self.default_value,
            'is_identity': self.is_identity,
            'description': self.description,
            'is_computed': self.is_computed
        }


@dataclass
class Constraint:
    """Класс, представляющий ограничение"""
    name: str
    type: ConstraintType
    table_name: str
    columns: List[str] = field(default_factory=list)
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None
    check_expression: Optional[str] = None
    definition: Optional[str] = None
    is_deferrable: bool = False
    is_deferred: bool = False

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'type': self.type.value,
            'table_name': self.table_name,
            'columns': self.columns,
            'referenced_table': self.referenced_table,
            'check_expression': self.check_expression
        }


@dataclass
class Index:
    """Класс, представляющий индекс"""
    name: str
    table_name: str
    columns: List[str] = field(default_factory=list)
    is_unique: bool = False
    is_primary: bool = False
    index_type: str = "btree"
    definition: Optional[str] = None
    where_clause: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'table_name': self.table_name,
            'columns': self.columns,
            'is_unique': self.is_unique,
            'is_primary': self.is_primary,
            'index_type': self.index_type
        }


@dataclass
class Trigger:
    """Класс, представляющий триггер"""
    name: str
    table_name: str
    function_name: str
    event: TriggerEvent
    timing: TriggerTiming
    is_enabled: bool = True
    condition: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'table_name': self.table_name,
            'function_name': self.function_name,
            'event': self.event.value,
            'timing': self.timing.value,
            'is_enabled': self.is_enabled
        }


@dataclass
class Function:
    """Класс, представляющий функцию/процедуру"""
    name: str
    schema_name: str
    language: str
    return_type: Optional[str] = None
    is_aggregate: bool = False
    is_window: bool = False
    is_strict: bool = False
    is_volatile: bool = True
    arguments: List[Dict[str, str]] = field(default_factory=list)
    definition: Optional[str] = None
    description: Optional[str] = None
    source_code: Optional[str] = None
    business_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schema': self.schema_name,
            'language': self.language,
            'return_type': self.return_type,
            'arguments': self.arguments,
            'business_rules': self.business_rules
        }


@dataclass
class Table:
    """Класс, представляющий таблицу"""
    name: str
    schema_name: str = "public"
    columns: List[Column] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)
    triggers: List[Trigger] = field(default_factory=list)
    description: Optional[str] = None
    row_count: Optional[int] = None

    def get_primary_key(self) -> Optional[Constraint]:
        for c in self.constraints:
            if c.type == ConstraintType.PRIMARY_KEY:
                return c
        return None

    def get_foreign_keys(self) -> List[Constraint]:
        return [c for c in self.constraints if c.type == ConstraintType.FOREIGN_KEY]

    def get_columns_by_name(self, column_name: str) -> Optional[Column]:
        for col in self.columns:
            if col.name == column_name:
                return col
        return None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schema': self.schema_name,
            'columns': [c.to_dict() for c in self.columns],
            'constraints': [c.to_dict() for c in self.constraints],
            'indexes': [i.to_dict() for i in self.indexes],
            'description': self.description
        }


@dataclass
class BusinessRule:
    """Класс, представляющий бизнес-правило"""
    name: str
    rule_type: str
    table_name: Optional[str] = None
    expression: Optional[str] = None
    description: Optional[str] = None
    source_code: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)