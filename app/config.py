"""
应用配置文件
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # MongoDB 配置
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB_NAME: str = "apt_entity_db"
    MONGO_USERNAME: Optional[str] = None
    MONGO_PASSWORD: Optional[str] = None
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Sentence-BERT 模型配置
    # 使用本地模型路径（指向实际的模型文件目录）
    BERT_MODEL_PATH: str = "app/model/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    
    # 算法阈值配置
    LEVENSHTEIN_THRESHOLD: float = 0.8
    SEMANTIC_THRESHOLD: float = 0.75
    
    # 缓存配置
    CACHE_VECTOR_TTL: int = 7 * 24 * 3600  # 向量缓存7天
    CACHE_QUERY_TTL: int = 3600  # 查询结果缓存1小时
    
    # API 配置
    API_TITLE: str = "APT 威胁实体跨文本对齐工具 API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "提供词典管理和实体对齐服务"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

