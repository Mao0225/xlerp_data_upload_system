from pydantic import BaseModel
from typing import Any, Dict


class BaseSource(BaseModel):
    class Config:
        extra = "allow"  # 允许动态字段，从 SQL AS 结果

    def __init__(self, **data: Any):
        super().__init__(**data)