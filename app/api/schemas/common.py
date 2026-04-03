"""
通用响应模型
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """标准 API 响应格式"""
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="提示信息")
    data: Optional[Any] = Field(default=None, description="业务数据")

