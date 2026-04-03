"""
词典管理模块 (MongoDictManager)
负责实体的全生命周期管理和词典自更新
"""

from typing import Dict, List, Optional, Any,Tuple
from datetime import datetime, timezone
import uuid
from app.services.database import db_service
from app.services.cache import cache_service
from app.utils.logger import setup_logger
from app.utils.validators import validate_entity_data, validate_query_params

logger = setup_logger(__name__)

# 实体类型到集合名称的映射
ENTITY_TYPE_TO_COLLECTION = {
    "apt": "apt_organizations",
    "tool": "attack_tools",
    "vuln": "vulnerabilities"
}

# 用户格式到系统格式的实体类型映射
USER_ENTITY_TYPE_MAP = {
    "apt_organization": "apt",
    "attack_tool": "tool",
    "vulnerability": "vuln"
}


class MongoDictManager:
    """MongoDB 词典管理器"""
    
    def __init__(self):
        self.db_service = db_service
        self.cache_service = cache_service
    
    def init_mongo_conn(
        self,
        host: str = "localhost",
        port: int = 27017,
        db_name: str = "apt_entity_db",
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        初始化 MongoDB 连接
        
        Args:
            host: MongoDB 主机地址
            port: MongoDB 端口
            db_name: 数据库名称
        
        Returns:
            (连接是否成功, 错误信息)
        """
        # 连接数据库
        success, error_msg = self.db_service.connect(host, port, db_name, username, password)
        if not success:
            return False, error_msg
        
        # 创建集合和索引
        if not self.db_service.create_collections_and_indexes():
            return False, "创建集合和索引失败"
        
        logger.info("MongoDB 连接初始化成功")
        return True, None
    
    def query_entity(
        self,
        query_params: Dict[str, Any],
        entity_type: str
    ) -> Tuple[List[Dict], int]:
        """
        查询实体
        
        Args:
            query_params: 查询参数字典（支持按核心名称、变体等查询）
            entity_type: 实体类型 (apt/tool/vuln)
        
        Returns:
            (实体列表, 数量)
        """
        try:
            # 校验查询参数
            is_valid, error_msg = validate_query_params(query_params)
            if not is_valid:
                logger.warning(f"查询参数校验失败: {error_msg}")
                return [], 0
            
            # 获取集合
            collection_name = ENTITY_TYPE_TO_COLLECTION.get(entity_type)
            if not collection_name:
                logger.error(f"无效的实体类型: {entity_type}")
                return [], 0
            
            collection = self.db_service.get_collection(collection_name)
            if collection is None:
                return [], 0
            
            # 构建查询条件
            mongo_query = {}
            
            # 如果提供了 entity_id，精确匹配
            if "entity_id" in query_params and query_params["entity_id"]:
                mongo_query["entity_id"] = query_params["entity_id"]
            
            # 如果提供了 keyword，在核心名称、变体和描述中搜索
            if "keyword" in query_params and query_params["keyword"]:
                keyword = query_params["keyword"]
                mongo_query["$or"] = [
                    {"en_core": {"$regex": keyword, "$options": "i"}},
                    {"zh_core": {"$regex": keyword, "$options": "i"}},
                    {"en_variants": {"$regex": keyword, "$options": "i"}},
                    {"zh_variants": {"$regex": keyword, "$options": "i"}},
                    {"description": {"$regex": keyword, "$options": "i"}}
                ]
            else:
                # 精确匹配核心名称
                if "en_core" in query_params:
                    mongo_query["en_core"] = query_params["en_core"]
                if "zh_core" in query_params:
                    mongo_query["zh_core"] = query_params["zh_core"]
                
                # 变体匹配（使用 $in 操作符）
                or_conditions = []
                if "en_variants" in query_params:
                    variant = query_params["en_variants"]
                    if isinstance(variant, str):
                        or_conditions.append({"en_variants": variant})
                    elif isinstance(variant, list):
                        or_conditions.append({"en_variants": {"$in": variant}})
                
                if "zh_variants" in query_params:
                    variant = query_params["zh_variants"]
                    if isinstance(variant, str):
                        or_conditions.append({"zh_variants": variant})
                    elif isinstance(variant, list):
                        or_conditions.append({"zh_variants": {"$in": variant}})
                
                if or_conditions:
                    if "$or" in mongo_query:
                        mongo_query["$or"].extend(or_conditions)
                    else:
                        mongo_query["$or"] = or_conditions
            
            # 执行查询
            entities = list(collection.find(mongo_query))
            
            # 转换 ObjectId 和 datetime 为字符串
            for entity in entities:
                if "_id" in entity:
                    entity["_id"] = str(entity["_id"])
                # 转换 datetime 对象为 ISO 格式字符串
                if "create_time" in entity and isinstance(entity["create_time"], datetime):
                    entity["create_time"] = entity["create_time"].isoformat()
                if "last_update_time" in entity and isinstance(entity["last_update_time"], datetime):
                    entity["last_update_time"] = entity["last_update_time"].isoformat()
                # 转换 update_log 中的 datetime
                if "update_log" in entity and isinstance(entity["update_log"], list):
                    for log_entry in entity["update_log"]:
                        if isinstance(log_entry, dict) and "time" in log_entry:
                            if isinstance(log_entry["time"], datetime):
                                log_entry["time"] = log_entry["time"].isoformat()
            
            count = len(entities)
            logger.info(f"查询到 {count} 个 {entity_type} 实体")
            
            return entities, count
            
        except Exception as e:
            logger.error(f"查询实体失败: {str(e)}")
            return [], 0
    
    def add_entity(
        self,
        entity_data: Dict[str, Any],
        entity_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        新增实体
        
        Args:
            entity_data: 实体数据字典
            entity_type: 实体类型 (apt/tool/vuln)
        
        Returns:
            (是否成功, 实体ID, 错误信息)
        """
        try:
            # 校验实体数据
            is_valid, error_msg = validate_entity_data(entity_data, entity_type)
            if not is_valid:
                return False, None, error_msg
            
            # 获取集合
            collection_name = ENTITY_TYPE_TO_COLLECTION.get(entity_type)
            if not collection_name:
                return False, None, f"无效的实体类型: {entity_type}"
            
            collection = self.db_service.get_collection(collection_name)
            if collection is None:
                return False, None, "数据库未连接"
            
            # 生成 entity_id（如果未提供）
            if "entity_id" not in entity_data or not entity_data["entity_id"]:
                # 根据实体类型确定前缀
                if entity_type == "apt":
                    prefix = "APT"
                elif entity_type == "tool":
                    prefix = "TOOL"
                elif entity_type == "vuln":
                    prefix = "VULN"
                else:
                    return False, None, f"无效的实体类型: {entity_type}"

                # 获取当前集合中的实体数量
                total_count = collection.count_documents({})
                entity_id = f"{prefix}-{total_count + 1:03d}"
            else:
                entity_id = entity_data["entity_id"].upper()  # 统一转为大写
                # 检查 entity_id 是否已存在
                if collection.find_one({"entity_id": entity_id}):
                    return False, None, f"实体ID {entity_id} 已存在"
            
            # 准备插入数据
            now = datetime.now(timezone.utc)
            insert_data = {
                "entity_id": entity_id,
                "en_core": entity_data["en_core"],
                "zh_core": entity_data["zh_core"],
                "en_variants": entity_data.get("en_variants", []),
                "zh_variants": entity_data.get("zh_variants", []),
                "description": entity_data.get("description"),
                "create_time": now,
                "last_update_time": now,
                "update_log": []
            }
            
            # 插入数据库
            result = collection.insert_one(insert_data)
            
            if result.inserted_id:
                # 记录操作日志
                operate_content = f"新增实体: {entity_data['en_core']} / {entity_data['zh_core']}"
                self._log_operation("add", entity_type, entity_id, operate_content)
                
                logger.info(f"成功新增实体: {entity_id}")
                return True, entity_id, None
            else:
                return False, None, "插入数据库失败"
                
        except Exception as e:
            error_msg = f"新增实体失败: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def update_entity(
        self,
        entity_id: str,
        update_data: Dict[str, Any],
        entity_type: str
    ) -> Tuple[bool, int]:
        """
        更新实体
        
        Args:
            entity_id: 实体ID
            update_data: 更新数据字典
            entity_type: 实体类型 (apt/tool/vuln)
        
        Returns:
            (是否成功, 更新数量)
        """
        try:
            # 获取集合
            collection_name = ENTITY_TYPE_TO_COLLECTION.get(entity_type)
            if not collection_name:
                logger.error(f"无效的实体类型: {entity_type}")
                return False, 0
            
            collection = self.db_service.get_collection(collection_name)
            if collection is None:
                return False, 0
            
            # 检查实体是否存在
            existing_entity = collection.find_one({"entity_id": entity_id})
            if not existing_entity:
                logger.warning(f"实体不存在: {entity_id}")
                return False, 0
            
            # 检查是否更新了核心名称（需要清除缓存）
            need_clear_cache = False
            if "en_core" in update_data or "zh_core" in update_data:
                need_clear_cache = True
            
            # 构建更新内容描述
            update_fields = []
            for key in ["en_core", "zh_core", "en_variants", "zh_variants", "description"]:
                if key in update_data:
                    update_fields.append(key)
            
            # 准备更新数据
            now = datetime.now(timezone.utc)
            update_doc = {
                "$set": {
                    "last_update_time": now
                },
                "$push": {
                    "update_log": {
                        "operate_type": "update",
                        "content": f"更新字段: {', '.join(update_fields)}",
                        "time": now
                    }
                }
            }
            
            # 添加要更新的字段
            for key, value in update_data.items():
                if key in ["en_core", "zh_core", "en_variants", "zh_variants", "description"]:
                    update_doc["$set"][key] = value
            
            # 执行更新
            result = collection.update_one(
                {"entity_id": entity_id},
                update_doc
            )
            
            if result.modified_count > 0:
                # 如果更新了核心名称，清除缓存
                if need_clear_cache and self.cache_service.is_connected:
                    self.cache_service.delete_cache(f"vector:{entity_id}")
                
                # 记录操作日志
                operate_content = f"更新实体字段: {', '.join(update_fields)}"
                self._log_operation("update", entity_type, entity_id, operate_content)
                
                logger.info(f"成功更新实体: {entity_id}，修改了 {result.modified_count} 条记录")
                return True, result.modified_count
            else:
                logger.warning(f"更新实体失败，未找到匹配的记录: {entity_id}")
                return False, 0
                
        except Exception as e:
            logger.error(f"更新实体失败: {str(e)}")
            return False, 0
    
    def delete_entity(
        self,
        entity_id: str,
        entity_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        删除实体
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型 (apt/tool/vuln)
        
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 获取集合
            collection_name = ENTITY_TYPE_TO_COLLECTION.get(entity_type)
            if not collection_name:
                return False, f"无效的实体类型: {entity_type}"
            
            collection = self.db_service.get_collection(collection_name)
            if collection is None:
                return False, "数据库未连接"
            
            # 检查实体是否存在
            existing_entity = collection.find_one({"entity_id": entity_id})
            if not existing_entity:
                return False, f"实体不存在: {entity_id}"
            
            # 获取实体信息用于日志
            en_core = existing_entity.get("en_core", "")
            zh_core = existing_entity.get("zh_core", "")
            
            # 删除实体
            result = collection.delete_one({"entity_id": entity_id})
            
            if result.deleted_count > 0:
                # 清除相关缓存
                if self.cache_service.is_connected:
                    self.cache_service.delete_cache(f"vector:{entity_id}")
                
                # 记录操作日志
                operate_content = f"删除实体: {en_core} / {zh_core}"
                self._log_operation("delete", entity_type, entity_id, operate_content)
                
                logger.info(f"成功删除实体: {entity_id}")
                return True, None
            else:
                return False, "删除失败，未找到匹配的记录"
                
        except Exception as e:
            error_msg = f"删除实体失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def sync_manual_correction(
        self,
        entity_id: str,
        correction_data: Dict[str, Any],
        entity_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        同步人工修正结果（词典自更新）
        
        Args:
            entity_id: 实体ID
            correction_data: 修正数据（通常是新增的变体）
            entity_type: 实体类型
        
        Returns:
            (是否成功, 错误信息)
        """
        # 调用 update_entity() 同步修正数据
        success, update_count = self.update_entity(entity_id, correction_data, entity_type)
        
        if success:
            # 记录自更新日志
            operate_content = f"人工修正同步: {correction_data}"
            self._log_operation("update", entity_type, entity_id, operate_content, operator="manual_correction")
            logger.info(f"成功同步人工修正: {entity_id}")
            return True, None
        else:
            return False, "同步人工修正失败"
    
    def _log_operation(
        self,
        operate_type: str,
        entity_type: str,
        entity_id: str,
        operate_content: str,
        operator: str = "system",
        ip_address: Optional[str] = None
    ):
        """
        记录操作日志
        
        Args:
            operate_type: 操作类型 (add/update/delete/query)
            entity_type: 实体类型
            entity_id: 实体ID
            operate_content: 操作内容
            operator: 操作者
            ip_address: 操作IP地址
        """
        try:
            log_collection = self.db_service.get_collection("dict_operation_logs")
            if log_collection is None:
                logger.warning("无法获取日志集合，跳过日志记录")
                return
            
            # 生成日志ID
            log_id = f"log-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
            
            # 构建日志文档
            log_doc = {
                "log_id": log_id,
                "operator": operator,
                "operate_type": operate_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "operate_content": operate_content,
                "operate_time": datetime.now(timezone.utc),
                "ip_address": ip_address
            }
            
            # 插入日志
            log_collection.insert_one(log_doc)
            logger.debug(f"已记录操作日志: {log_id}")
            
        except Exception as e:
            logger.error(f"记录操作日志失败: {str(e)}")
    
    def get_operation_logs(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        查询操作日志
        
        Args:
            entity_id: 实体ID（可选）
            entity_type: 实体类型（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回数量限制
        
        Returns:
            日志列表
        """
        try:
            log_collection = self.db_service.get_collection("dict_operation_logs")
            if log_collection is None:
                return []
            
            # 构建查询条件
            query = {}
            if entity_id:
                query["entity_id"] = entity_id
            if entity_type:
                query["entity_type"] = entity_type
            if start_time or end_time:
                query["operate_time"] = {}
                if start_time:
                    query["operate_time"]["$gte"] = start_time
                if end_time:
                    query["operate_time"]["$lte"] = end_time
            
            # 执行查询，按时间倒序
            logs = list(log_collection.find(query).sort("operate_time", -1).limit(limit))
            
            # 转换 ObjectId 和 datetime 为字符串
            for log in logs:
                if "_id" in log:
                    log["_id"] = str(log["_id"])
                # 转换 datetime 对象为 ISO 格式字符串
                if "operate_time" in log and isinstance(log["operate_time"], datetime):
                    log["operate_time"] = log["operate_time"].isoformat()
            
            return logs
            
        except Exception as e:
            logger.error(f"查询操作日志失败: {str(e)}")
            return []
    
    def batch_add_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        批量添加实体
        
        Args:
            entities: 实体列表（用户格式）
        
        Returns:
            (成功数量, 失败数量, 详细结果列表)
        """
        success_count = 0
        fail_count = 0
        results = []
        
        for entity in entities:
            try:
                # 转换用户格式到系统格式
                converted_entity, entity_type = self._convert_user_format_to_system(entity)
                
                if not converted_entity:
                    fail_count += 1
                    results.append({
                        "entity_id": entity.get("entity_id"),
                        "success": False,
                        "error_msg": f"实体类型转换失败: {entity.get('entity_type')}"
                    })
                    continue
                
                # 调用单个添加方法
                success, entity_id, error_msg = self.add_entity(
                    entity_data=converted_entity,
                    entity_type=entity_type
                )
                
                if success:
                    success_count += 1
                    results.append({
                        "entity_id": entity_id,
                        "success": True,
                        "error_msg": None
                    })
                else:
                    fail_count += 1
                    results.append({
                        "entity_id": entity.get("entity_id"),
                        "success": False,
                        "error_msg": error_msg
                    })
                    
            except Exception as e:
                fail_count += 1
                error_msg = f"处理实体时发生异常: {str(e)}"
                logger.error(f"{error_msg}, 实体数据: {entity}")
                results.append({
                    "entity_id": entity.get("entity_id"),
                    "success": False,
                    "error_msg": error_msg
                })
        
        return success_count, fail_count, results
    
    def _convert_user_format_to_system(self, user_entity: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        将用户格式的实体转换为系统格式
        
        Args:
            user_entity: 用户格式的实体字典
        
        Returns:
            (转换后的实体字典, 实体类型) 或 (None, None) 如果转换失败
        """
        try:
            # 转换 entity_type
            user_entity_type = user_entity.get("entity_type", "").lower()
            system_entity_type = USER_ENTITY_TYPE_MAP.get(user_entity_type)
            
            if not system_entity_type:
                return None, None
            
            # 构建系统格式的实体数据
            system_entity = {
                "entity_id": user_entity.get("entity_id"),
                "en_core": user_entity.get("en_core", ""),
                "zh_core": user_entity.get("cn_core"),  # cn_core -> zh_core（现在可以为None）
                "en_variants": user_entity.get("en_variants", []),
                "zh_variants": user_entity.get("zh_variants", []),
                "description": user_entity.get("description")
            }
            
            return system_entity, system_entity_type
            
        except Exception as e:
            logger.error(f"转换实体格式失败: {str(e)}")
            return None, None

