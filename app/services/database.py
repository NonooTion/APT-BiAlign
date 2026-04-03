"""
MongoDB 数据库服务模块
负责数据库连接、集合管理和索引创建
"""

from typing import Optional,Tuple
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseService:
    """MongoDB 数据库服务类"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._connected = False
    
    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        连接 MongoDB 数据库
        
        Args:
            host: MongoDB 主机地址
            port: MongoDB 端口
            db_name: 数据库名称
        
        Returns:
            (连接是否成功, 错误信息)
        """
        try:
            # 使用传入参数或配置默认值
            host = host or settings.MONGO_HOST
            port = port or settings.MONGO_PORT
            db_name = db_name or settings.MONGO_DB_NAME
            
            # 构建连接字符串
            # 优先使用传入的用户名密码，否则使用配置中的
            mongo_username = username or settings.MONGO_USERNAME
            mongo_password = password or settings.MONGO_PASSWORD
            
            if mongo_username and mongo_password:
                connection_string = f"mongodb://{mongo_username}:{mongo_password}@{host}:{port}/{db_name}?authSource=admin"
            else:
                connection_string = f"mongodb://{host}:{port}/"
            
            # 创建 MongoClient 实例
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            
            # 测试连接
            self.client.admin.command('ping')
            
            # 获取数据库对象
            self.db = self.client[db_name]
            
            # 标记为已连接
            self._connected = True
            
            logger.info(f"成功连接到 MongoDB: {host}:{port}/{db_name}")
            return True, None
            
        except Exception as e:
            error_msg = f"连接 MongoDB 失败: {str(e)}"
            logger.error(error_msg)
            self._connected = False
            return False, error_msg
    
    def create_collections_and_indexes(self) -> bool:
        """
        创建业务集合和索引
        
        Returns:
            是否创建成功
        """
        if not self._connected or self.db is None:
            logger.error("数据库未连接，无法创建集合和索引")
            return False
        
        try:
            # 业务集合名称
            business_collections = ["apt_organizations", "attack_tools", "vulnerabilities"]
            
            # 为每个业务集合创建索引
            for collection_name in business_collections:
                collection = self.db[collection_name]
                
                # 创建唯一索引：entity_id
                collection.create_index("entity_id", unique=True, name="idx_entity_id_unique")
                
                # 创建普通索引：en_core, zh_core
                collection.create_index("en_core", name="idx_en_core")
                collection.create_index("zh_core", name="idx_zh_core")
                
                # 创建数组索引：en_variants, zh_variants
                collection.create_index("en_variants", name="idx_en_variants")
                collection.create_index("zh_variants", name="idx_zh_variants")
                
                logger.info(f"已为集合 {collection_name} 创建索引")
            
            # 创建日志集合
            log_collection = self.db["dict_operation_logs"]
            
            # 为日志集合创建索引
            log_collection.create_index("operate_time", name="idx_operate_time")
            log_collection.create_index("entity_id", name="idx_log_entity_id")
            log_collection.create_index([("entity_type", 1), ("operate_time", -1)], name="idx_entity_type_time")
            
            logger.info("已为日志集合创建索引")
            return True
            
        except Exception as e:
            logger.error(f"创建集合和索引失败: {str(e)}")
            return False
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        获取集合对象
        
        Args:
            collection_name: 集合名称
        
        Returns:
            集合对象
        """
        if not self._connected or self.db is None:
            logger.error("数据库未连接，无法获取集合")
            return None
        
        try:
            return self.db[collection_name]
        except Exception as e:
            logger.error(f"获取集合 {collection_name} 失败: {str(e)}")
            return None
    
    def disconnect(self):
        """断开数据库连接"""
        if self.client is not None:
            try:
                self.client.close()
                self._connected = False
                self.db = None
                logger.info("已断开 MongoDB 连接")
            except Exception as e:
                logger.error(f"断开 MongoDB 连接失败: {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected


# 全局数据库服务实例
db_service = DatabaseService()

