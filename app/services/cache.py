"""
Redis 缓存服务模块
负责实体向量缓存和查询结果缓存
"""

from typing import Optional, Tuple,Any
import json
import redis
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CacheService:
    """Redis 缓存服务类"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        连接 Redis 服务器
        
        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: Redis 数据库编号
            password: Redis 密码
        
        Returns:
            (连接是否成功, 错误信息)
        """
        try:
            # 使用传入参数或配置默认值
            host = host or settings.REDIS_HOST
            port = port or settings.REDIS_PORT
            db = db or settings.REDIS_DB
            password = password or settings.REDIS_PASSWORD
            
            # 创建 Redis 客户端
            if password:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=False,  # 保持二进制模式以便存储向量
                    socket_connect_timeout=5
                )
            else:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=False,
                    socket_connect_timeout=5
                )
            
            # 测试连接
            self.client.ping()
            
            self._connected = True
            logger.info(f"成功连接到 Redis: {host}:{port}/{db}")
            return True, None
            
        except Exception as e:
            error_msg = f"连接 Redis 失败: {str(e)}"
            logger.error(error_msg)
            self._connected = False
            self.client = None
            return False, error_msg
    
    def set_vector_cache(self, entity_id: str, vector: list, ttl: Optional[int] = None) -> bool:
        """
        缓存实体向量
        
        Args:
            entity_id: 实体ID
            vector: 向量数据（列表或 numpy 数组）
            ttl: 过期时间（秒），默认使用配置值
        
        Returns:
            是否缓存成功
        """
        if not self._connected or self.client is None:
            return False
        
        try:
            # 将向量转换为列表（如果是 numpy 数组）
            if hasattr(vector, 'tolist'):
                vector_list = vector.tolist()
            else:
                vector_list = list(vector)
            
            # 序列化为 JSON
            vector_json = json.dumps(vector_list)
            
            # 构建缓存键
            cache_key = f"vector:{entity_id}"
            
            # 设置过期时间
            if ttl is None:
                ttl = settings.CACHE_VECTOR_TTL
            
            # 存储到 Redis
            self.client.setex(cache_key, ttl, vector_json)
            
            logger.debug(f"已缓存实体向量: {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"缓存实体向量失败: {str(e)}")
            return False
    
    def get_vector_cache(self, entity_id: str) -> Optional[list]:
        """
        获取缓存的实体向量
        
        Args:
            entity_id: 实体ID
        
        Returns:
            向量数据（列表），如果不存在则返回 None
        """
        if not self._connected or self.client is None:
            return None
        
        try:
            # 构建缓存键
            cache_key = f"vector:{entity_id}"
            
            # 从 Redis 获取
            vector_json = self.client.get(cache_key)
            
            if vector_json is None:
                return None
            
            # 反序列化
            vector_list = json.loads(vector_json)
            
            logger.debug(f"从缓存获取实体向量: {entity_id}")
            return vector_list
            
        except Exception as e:
            logger.error(f"获取实体向量缓存失败: {str(e)}")
            return None
    
    def set_query_cache(self, cache_key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        缓存查询结果
        
        Args:
            cache_key: 缓存键
            data: 要缓存的数据
            ttl: 过期时间（秒），默认使用配置值
        
        Returns:
            是否缓存成功
        """
        if not self._connected or self.client is None:
            return False
        
        try:
            # 序列化为 JSON
            data_json = json.dumps(data, ensure_ascii=False, default=str)
            
            # 设置过期时间
            if ttl is None:
                ttl = settings.CACHE_QUERY_TTL
            
            # 存储到 Redis
            self.client.setex(cache_key, ttl, data_json)
            
            return True
            
        except Exception as e:
            logger.error(f"缓存查询结果失败: {str(e)}")
            return False
    
    def get_query_cache(self, cache_key: str) -> Optional[Any]:
        """
        获取缓存的查询结果
        
        Args:
            cache_key: 缓存键
        
        Returns:
            缓存的数据，如果不存在则返回 None
        """
        if not self._connected or self.client is None:
            return None
        
        try:
            # 从 Redis 获取
            data_json = self.client.get(cache_key)
            
            if data_json is None:
                return None
            
            # 反序列化
            data = json.loads(data_json)
            
            return data
            
        except Exception as e:
            logger.error(f"获取查询缓存失败: {str(e)}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        if not self._connected or self.client is None:
            return False
        
        try:
            # 删除缓存
            result = self.client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开 Redis 连接"""
        if self.client is not None:
            try:
                self.client.close()
                self._connected = False
                self.client = None
                logger.info("已断开 Redis 连接")
            except Exception as e:
                logger.error(f"断开 Redis 连接失败: {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected


# 全局缓存服务实例
cache_service = CacheService()

