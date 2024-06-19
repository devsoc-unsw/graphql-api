from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Metadata(BaseModel):
    table_name: str
    sql_before: Optional[str] = Field(None, description='command to execute before running the insert')
    sql_after: Optional[str] = Field(None, description='command to execute after running the insert')
    sql_up: str         # SQL to set UP table and related data types/indexes
    sql_down: str       # SQL to tear DOWN a table (should be the opp. of up)
    columns: list[str]  # list of column names that require insertion
    write_mode: Literal['append', 'overwrite'] = Field('overwrite', description='mode in which to write to the database')


class BatchRequest(BaseModel):
    metadata: Metadata
    payload: list[Any]


class CreateTableResult(Enum):
    NONE = 0
    UPDATED = 1
    CREATED = 2