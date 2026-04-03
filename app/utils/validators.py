"""
参数校验工具模块
"""

from typing import Any, Dict, List, Optional,Tuple
import re


def validate_entity_data(entity_data: Dict[str, Any], entity_type: str) -> Tuple[bool, Optional[str]]:
    """
    校验实体数据的完整性
    
    Args:
        entity_data: 实体数据字典
        entity_type: 实体类型 (apt/tool/vuln)
    
    Returns:
        (校验是否通过, 错误信息)
    """
    # 检查实体类型
    valid_entity_types = ["apt", "tool", "vuln"]
    if entity_type not in valid_entity_types:
        return False, f"无效的实体类型: {entity_type}，必须是 {valid_entity_types} 之一"
    
    # 检查必需字段：en_core（zh_core可选）
    if "en_core" not in entity_data or not entity_data["en_core"]:
        return False, "缺少必需字段: en_core（英文核心名称）"

    # zh_core 现在是可选字段，如果提供则必须是字符串
    if "zh_core" in entity_data and entity_data["zh_core"] is not None:
        if not isinstance(entity_data["zh_core"], str):
            return False, "zh_core 必须是字符串类型"
    
    # 检查核心名称类型
    if not isinstance(entity_data["en_core"], str):
        return False, "en_core 必须是字符串类型"

    # zh_core 现在是可选的，如果提供则必须是字符串
    if "zh_core" in entity_data and entity_data["zh_core"] is not None and not isinstance(entity_data["zh_core"], str):
        return False, "zh_core 必须是字符串类型"
    
    # 检查 entity_id 类型（如果提供）
    if "entity_id" in entity_data and entity_data["entity_id"]:
        entity_id = entity_data["entity_id"]
        if not isinstance(entity_id, str):
            return False, "entity_id 必须是字符串类型"
        # 不限制 entity_id 格式，允许任意字符串
    
    # 检查变体字段格式
    if "en_variants" in entity_data:
        if not isinstance(entity_data["en_variants"], list):
            return False, "en_variants 必须是列表类型"
        for variant in entity_data["en_variants"]:
            if not isinstance(variant, str):
                return False, "en_variants 中的元素必须是字符串类型"
    
    if "zh_variants" in entity_data:
        if not isinstance(entity_data["zh_variants"], list):
            return False, "zh_variants 必须是列表类型"
        for variant in entity_data["zh_variants"]:
            if not isinstance(variant, str):
                return False, "zh_variants 中的元素必须是字符串类型"
    
    # 检查描述字段格式（可选字段）
    if "description" in entity_data and entity_data["description"] is not None:
        if not isinstance(entity_data["description"], str):
            return False, "description 必须是字符串类型"
        # 限制描述长度（可选，建议不超过 2000 字符）
        if len(entity_data["description"]) > 2000:
            return False, "description 长度不能超过 2000 个字符"
    
    return True, None


def validate_query_params(query_params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    校验查询参数
    
    Args:
        query_params: 查询参数字典
    
    Returns:
        (校验是否通过, 错误信息)
    """
    if not isinstance(query_params, dict):
        return False, "query_params 必须是字典类型"
    
    # 允许的查询字段
    allowed_fields = ["entity_id", "en_core", "zh_core", "en_variants", "zh_variants", "keyword", "description"]
    
    # 检查是否有无效字段
    for key in query_params.keys():
        if key not in allowed_fields:
            return False, f"不支持的查询字段: {key}，允许的字段: {allowed_fields}"
    
    # 如果提供了 keyword，检查是否为字符串
    if "keyword" in query_params:
        if not isinstance(query_params["keyword"], str):
            return False, "keyword 必须是字符串类型"
    
    return True, None


def validate_text_chunk(text_chunk: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    校验文本片段数据
    
    Args:
        text_chunk: 文本片段字典
    
    Returns:
        (校验是否通过, 错误信息)
    """
    # TODO: 实现文本片段校验逻辑
    # 检查必需字段：text, language 等
    pass

