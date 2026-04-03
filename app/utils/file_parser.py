"""
文件解析工具模块
支持 JSON 和 TXT 文件解析
"""

import os
from typing import List, Tuple, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_txt_file(file_path: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    解析 TXT 文件（返回整个文本内容，留给后续处理分词分句）

    Args:
        file_path: 文件路径

    Returns:
        (是否成功, 错误信息, 文本列表)
    """
    logger.info(f"[CALL] parse_txt_file(file_path={file_path})")
    try:
        # 尝试 UTF-8 编码
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试 GBK 编码
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 返回整个文本内容作为单个候选项，由后续模块进行分词分句处理
        candidates = [content.strip()] if content.strip() else []
        
        logger.info(f"成功解析 TXT 文件: {file_path}，文本长度: {len(content)} 字符")
        return True, None, candidates

    except Exception as e:
        error_msg = f"TXT 文件读取失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def parse_json_file(file_path: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    解析 JSON 文件

    Args:
        file_path: 文件路径

    Returns:
        (是否成功, 错误信息, 文本列表)
    """
    logger.info(f"[CALL] parse_json_file(file_path={file_path})")
    try:
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 从JSON数据中提取候选字符串
        candidates = _extract_candidates_from_json(data)

        logger.info(f"成功解析 JSON 文件: {file_path}，共提取 {len(candidates)} 个候选字符串")
        return True, None, candidates

    except json.JSONDecodeError as e:
        error_msg = f"JSON 解析失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            import json
            with open(file_path, 'r', encoding='gbk') as f:
                data = json.load(f)
            candidates = _extract_candidates_from_json(data)
            logger.info(f"成功解析 JSON 文件（GBK编码）: {file_path}，共提取 {len(candidates)} 个候选字符串")
            return True, None, candidates
        except Exception as e:
            error_msg = f"JSON 文件解析失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    except Exception as e:
        error_msg = f"JSON 文件读取失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def _extract_candidates_from_json(json_data) -> List[str]:
    """
    从JSON数据中提取候选字符串

    Args:
        json_data: JSON数据（可以是字典或列表）

    Returns:
        候选字符串列表
    """
    logger.info(f"[CALL] _extract_candidates_from_json(type={type(json_data).__name__})")
    candidates = []

    try:
        # 如果是直接的字符串数组
        if isinstance(json_data, list):
            candidates = json_data
        # 如果是字典格式
        elif isinstance(json_data, dict):
            # 提取group_set数组（如果存在）
            if "group_set" in json_data and isinstance(json_data["group_set"], list):
                candidates.extend(json_data["group_set"])

            # 提取tool_set数组（如果存在）
            if "tool_set" in json_data and isinstance(json_data["tool_set"], list):
                candidates.extend(json_data["tool_set"])

            # 提取vul_set数组（如果存在）
            if "vul_set" in json_data and isinstance(json_data["vul_set"], list):
                candidates.extend(json_data["vul_set"])

            # 如果字典中没有已知的数组字段，尝试提取所有字符串值
            if not candidates:
                for value in json_data.values():
                    if isinstance(value, list):
                        candidates.extend(value)
                    elif isinstance(value, str):
                        candidates.append(value)
        else:
            logger.warning(f"不支持的JSON数据类型: {type(json_data)}")
            return []

        # 去除空字符串和重复项
        candidates = [str(candidate).strip() for candidate in candidates if candidate and str(candidate).strip()]

        # 去重
        candidates = list(set(candidates))

    except Exception as e:
        logger.error(f"提取JSON候选字符串异常: {str(e)}")
        candidates = []

    return candidates


def parse_file(file_path: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    解析 JSON 或 TXT 文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        (是否成功, 错误信息, 候选字符串列表)
    """
    logger.info(f"[CALL] parse_file(file_path={file_path})")
    if not os.path.exists(file_path):
        error_msg = f"文件不存在: {file_path}"
        logger.error(error_msg)
        return False, error_msg, None
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.json':
        return parse_json_file(file_path)
    elif file_ext == '.txt':
        return parse_txt_file(file_path)
    else:
        error_msg = f"不支持的文件格式: {file_ext}，仅支持 JSON 或 TXT 格式"
        logger.error(error_msg)
        return False, error_msg, None

