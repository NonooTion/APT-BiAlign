"""
词典管理接口的数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class InitMongoRequest(BaseModel):
    """初始化 MongoDB 连接请求"""
    host: str = Field(default="localhost", description="MongoDB 主机地址")
    port: int = Field(default=27017, description="MongoDB 端口")
    db_name: str = Field(default="apt_entity_db", description="数据库名称")
    username: Optional[str] = Field(default=None, description="MongoDB 用户名（可选）")
    password: Optional[str] = Field(default=None, description="MongoDB 密码（可选）")


class InitMongoResponse(BaseModel):
    """初始化 MongoDB 连接响应"""
    conn_success: bool = Field(description="连接是否成功")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


class QueryEntityRequest(BaseModel):
    """查询实体请求"""
    query_params: Dict[str, Any] = Field(description="查询参数字典")
    entity_type: str = Field(description="实体类型 (apt/tool/vuln)")


class QueryEntityResponse(BaseModel):
    """查询实体响应"""
    entity_list: List[Dict[str, Any]] = Field(description="实体列表")
    count: int = Field(description="实体数量")


class EntityData(BaseModel):
    """实体数据模型"""
    entity_id: Optional[str] = Field(default=None, description="实体ID（可选，不提供则自动生成）")
    en_core: str = Field(description="英文核心名称")
    zh_core: Optional[str] = Field(default=None, description="中文核心名称（可选）")
    en_variants: Optional[List[str]] = Field(default=[], description="英文变体列表")
    zh_variants: Optional[List[str]] = Field(default=[], description="中文变体列表")
    description: Optional[str] = Field(default=None, description="实体描述（可选）")


class AddEntityRequest(BaseModel):
    """新增实体请求"""
    entity_data: EntityData = Field(description="实体数据")
    entity_type: str = Field(description="实体类型 (apt/tool/vuln)")


class AddEntityResponse(BaseModel):
    """新增实体响应"""
    add_success: bool = Field(description="是否成功")
    entity_id: Optional[str] = Field(default=None, description="实体ID")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


class UpdateEntityRequest(BaseModel):
    """更新实体请求"""
    entity_id: str = Field(description="实体ID")
    update_data: Dict[str, Any] = Field(description="更新数据字典")
    entity_type: str = Field(description="实体类型 (apt/tool/vuln)")


class UpdateEntityResponse(BaseModel):
    """更新实体响应"""
    update_success: bool = Field(description="是否成功")
    update_count: int = Field(description="更新数量")


class DeleteEntityRequest(BaseModel):
    """删除实体请求"""
    entity_id: str = Field(description="实体ID")
    entity_type: str = Field(description="实体类型 (apt/tool/vuln)")


class DeleteEntityResponse(BaseModel):
    """删除实体响应"""
    delete_success: bool = Field(description="是否成功")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


class BatchEntityItem(BaseModel):
    """批量导入的单个实体项（用户格式）"""
    entity_id: Optional[str] = Field(default=None, description="实体ID（可选）")
    entity_type: str = Field(description="实体类型 (apt_organization/attack_tool/vulnerability)")
    cn_core: Optional[str] = Field(default=None, description="中文核心名称（可选）")
    en_core: str = Field(description="英文核心名称")
    description: Optional[str] = Field(default=None, description="实体描述（可选）")
    zh_variants: Optional[List[str]] = Field(default=[], description="中文变体列表")
    en_variants: Optional[List[str]] = Field(default=[], description="英文变体列表")


class BatchAddRequest(BaseModel):
    """批量添加实体请求"""
    entities: List[BatchEntityItem] = Field(description="实体列表")


class BatchAddResult(BaseModel):
    """单个实体的批量添加结果"""
    entity_id: Optional[str] = Field(default=None, description="实体ID")
    success: bool = Field(description="是否成功")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


class BatchAddResponse(BaseModel):
    """批量添加响应"""
    total: int = Field(description="总数量")
    success_count: int = Field(description="成功数量")
    fail_count: int = Field(description="失败数量")
    results: List[BatchAddResult] = Field(description="详细结果列表")

