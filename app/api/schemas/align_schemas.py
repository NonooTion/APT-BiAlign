"""
对齐服务接口的数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InitAlgorithmRequest(BaseModel):
    """初始化算法请求"""
    bert_model_path: Optional[str] = Field(default=None, description="BERT 模型路径")
    levenshtein_thresh: Optional[float] = Field(default=0.8, description="模糊匹配阈值")
    semantic_thresh: Optional[float] = Field(default=0.75, description="语义匹配阈值")


class InitAlgorithmResponse(BaseModel):
    """初始化算法响应"""
    success: bool = Field(description="是否成功")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


class TextChunk(BaseModel):
    """文本片段模型"""
    text: str = Field(description="文本内容")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据（可选）")


class SingleTextAlignRequest(BaseModel):
    """单文本对齐请求"""
    text_chunk: TextChunk = Field(description="文本片段")
    entity_categories: List[str] = Field(default=["apt", "tool", "vuln"], description="要匹配的实体类别列表")


class AlignResult(BaseModel):
    """对齐结果模型"""
    entity_id: str = Field(description="实体ID")
    entity_type: str = Field(description="实体类型")
    en_core: str = Field(description="英文核心名称")
    zh_core: Optional[str] = Field(default=None, description="中文核心名称（可选）")
    match_type: str = Field(description="匹配类型 (exact/fuzzy/semantic)")
    confidence: float = Field(description="置信度")
    matched_text: str = Field(description="匹配到的文本片段")


class SingleTextAlignResponse(BaseModel):
    """单文本对齐响应"""
    align_result: List[AlignResult] = Field(description="对齐结果列表")
    process_time: float = Field(description="处理耗时（秒）")


class SetThresholdRequest(BaseModel):
    """设置阈值请求"""
    levenshtein_thresh: Optional[float] = Field(default=None, description="模糊匹配阈值")
    semantic_thresh: Optional[float] = Field(default=None, description="语义匹配阈值")


class SetThresholdResponse(BaseModel):
    """设置阈值响应"""
    success: bool = Field(description="是否成功")


class BatchTextAlignRequest(BaseModel):
    """批量文本对齐请求"""
    texts: List[TextChunk] = Field(description="文本片段列表")
    entity_categories: List[str] = Field(default=["apt", "tool", "vuln"], description="要匹配的实体类别列表")


class BatchTextAlignResponse(BaseModel):
    """批量文本对齐响应"""
    results: List[Dict[str, Any]] = Field(description="每个文本的对齐结果列表")
    total_process_time: float = Field(description="总处理耗时（秒）")


class EntityCorrectionRequest(BaseModel):
    """实体修正请求"""
    original_text: str = Field(description="原始匹配文本")
    corrected_entity_id: Optional[str] = Field(default=None, description="修正后的实体ID（如果为None，表示删除匹配）")
    align_result_id: Optional[str] = Field(default=None, description="对齐结果ID（用于标识）")


class EntityCorrectionResponse(BaseModel):
    """实体修正响应"""
    success: bool = Field(description="是否成功")
    updated_entity: Optional[Dict[str, Any]] = Field(default=None, description="更新后的实体信息")

