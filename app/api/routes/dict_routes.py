"""
词典管理接口路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.api.schemas.dict_schemas import (
    InitMongoRequest, InitMongoResponse,
    QueryEntityRequest, QueryEntityResponse,
    AddEntityRequest, AddEntityResponse,
    UpdateEntityRequest, UpdateEntityResponse,
    DeleteEntityRequest, DeleteEntityResponse,
    BatchAddRequest, BatchAddResponse, BatchAddResult
)
from app.api.schemas.common import StandardResponse
from app.core.dict_manager import MongoDictManager
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/dict", tags=["词典管理"])

# 全局词典管理器实例
dict_manager = MongoDictManager()


@router.post("/init", response_model=StandardResponse)
async def init_mongo_conn(request: InitMongoRequest):
    """
    初始化 MongoDB 连接
    
    - **host**: MongoDB 主机地址
    - **port**: MongoDB 端口
    - **db_name**: 数据库名称
    """
    try:
        success, error_msg = dict_manager.init_mongo_conn(
            host=request.host,
            port=request.port,
            db_name=request.db_name,
            username=request.username,
            password=request.password
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="MongoDB 连接初始化成功",
                data={"conn_success": True}
            )
        else:
            return StandardResponse(
                code=500,
                msg=error_msg or "MongoDB 连接初始化失败",
                data={"conn_success": False, "error_msg": error_msg}
            )
    except Exception as e:
        logger.error(f"初始化 MongoDB 连接异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"初始化失败: {str(e)}",
            data={"conn_success": False, "error_msg": str(e)}
        )


@router.get("/check", response_model=StandardResponse)
async def check_connection():
    """
    检查数据库连接状态
    """
    try:
        is_connected = dict_manager.db_service.is_connected
        if is_connected:
            return StandardResponse(
                code=200,
                msg="数据库已连接",
                data={
                    "connected": True,
                    "host": settings.MONGO_HOST,
                    "port": settings.MONGO_PORT,
                    "db_name": settings.MONGO_DB_NAME
                }
            )
        else:
            return StandardResponse(
                code=200,
                msg="数据库未连接",
                data={"connected": False}
            )
    except Exception as e:
        logger.error(f"检查连接状态异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"检查失败: {str(e)}",
            data={"connected": False}
        )


@router.get("/query", response_model=StandardResponse)
async def query_entity(
    entity_type: str = Query(..., description="实体类型 (apt/tool/vuln)"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    entity_id: Optional[str] = Query(None, description="实体ID"),
    en_core: Optional[str] = Query(None, description="英文核心名称"),
    zh_core: Optional[str] = Query(None, description="中文核心名称")
):
    """
    查询实体
    
    - **entity_type**: 实体类型 (apt/tool/vuln)
    - **keyword**: 关键词（在核心名称和变体中搜索）
    - **entity_id**: 实体ID（精确匹配）
    - **en_core**: 英文核心名称（精确匹配）
    - **zh_core**: 中文核心名称（精确匹配）
    """
    try:
        # 参数校验
        if entity_type not in ["apt", "tool", "vuln"]:
            return StandardResponse(
                code=400,
                msg=f"无效的实体类型: {entity_type}，必须是 apt/tool/vuln 之一",
                data={"entity_list": [], "count": 0}
            )
        
        # 构建查询参数字典
        query_params = {}
        if keyword:
            query_params["keyword"] = keyword
        if entity_id:
            query_params["entity_id"] = entity_id
        if en_core:
            query_params["en_core"] = en_core
        if zh_core:
            query_params["zh_core"] = zh_core
        
        # 调用查询方法
        entity_list, count = dict_manager.query_entity(query_params, entity_type)
        
        return StandardResponse(
            code=200,
            msg="查询成功",
            data={"entity_list": entity_list, "count": count}
        )
    except Exception as e:
        logger.error(f"查询实体异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"查询失败: {str(e)}",
            data={"entity_list": [], "count": 0}
        )


@router.post("/add", response_model=StandardResponse)
async def add_entity(request: AddEntityRequest):
    """
    新增实体
    
    - **entity_data**: 实体数据
    - **entity_type**: 实体类型 (apt/tool/vuln)
    """
    try:
        # 转换 Pydantic 模型为字典
        entity_data = request.entity_data.model_dump()
        
        # 调用新增方法
        success, entity_id, error_msg = dict_manager.add_entity(
            entity_data=entity_data,
            entity_type=request.entity_type
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="新增实体成功",
                data={"add_success": True, "entity_id": entity_id}
            )
        else:
            return StandardResponse(
                code=400,
                msg=error_msg or "新增实体失败",
                data={"add_success": False, "error_msg": error_msg}
            )
    except Exception as e:
        logger.error(f"新增实体异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"新增失败: {str(e)}",
            data={"add_success": False, "error_msg": str(e)}
        )


@router.put("/update", response_model=StandardResponse)
async def update_entity(request: UpdateEntityRequest):
    """
    更新实体
    
    - **entity_id**: 实体ID
    - **update_data**: 更新数据字典
    - **entity_type**: 实体类型 (apt/tool/vuln)
    """
    try:
        # 调用更新方法
        success, update_count = dict_manager.update_entity(
            entity_id=request.entity_id,
            update_data=request.update_data,
            entity_type=request.entity_type
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="更新实体成功",
                data={"update_success": True, "update_count": update_count}
            )
        else:
            return StandardResponse(
                code=400,
                msg="更新实体失败",
                data={"update_success": False, "update_count": 0}
            )
    except Exception as e:
        logger.error(f"更新实体异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"更新失败: {str(e)}",
            data={"update_success": False, "update_count": 0}
        )


@router.delete("/delete", response_model=StandardResponse)
async def delete_entity(request: DeleteEntityRequest):
    """
    删除实体
    
    - **entity_id**: 实体ID
    - **entity_type**: 实体类型 (apt/tool/vuln)
    """
    try:
        # 调用删除方法
        success, error_msg = dict_manager.delete_entity(
            entity_id=request.entity_id,
            entity_type=request.entity_type
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="删除实体成功",
                data={"delete_success": True}
            )
        else:
            return StandardResponse(
                code=400,
                msg=error_msg or "删除实体失败",
                data={"delete_success": False, "error_msg": error_msg}
            )
    except Exception as e:
        logger.error(f"删除实体异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"删除失败: {str(e)}",
            data={"delete_success": False, "error_msg": str(e)}
        )


@router.post("/batch-add", response_model=StandardResponse)
async def batch_add_entities(request: BatchAddRequest):
    """
    批量添加实体
    
    - **entities**: 实体列表（JSON格式）
    
    实体格式：
    {
      "entity_id": "APT-001",
      "entity_type": "apt_organization",
      "cn_core": "中文名称（可选）",
      "en_core": "English Name",
      "description": "描述",
      "zh_variants": ["变体1", "变体2"],
      "en_variants": ["variant1", "variant2"]
    }
    """
    try:
        # 转换 Pydantic 模型为字典列表
        entities = [item.model_dump() for item in request.entities]
        
        # 调用批量添加方法
        success_count, fail_count, results = dict_manager.batch_add_entities(entities)
        
        total = len(entities)
        
        return StandardResponse(
            code=200,
            msg=f"批量添加完成：成功 {success_count} 个，失败 {fail_count} 个",
            data={
                "total": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "results": results
            }
        )
    except Exception as e:
        logger.error(f"批量添加实体异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"批量添加失败: {str(e)}",
            data={
                "total": 0,
                "success_count": 0,
                "fail_count": 0,
                "results": []
            }
        )

