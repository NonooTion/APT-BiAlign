"""
FastAPI 应用主入口文件
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import dict_routes, align_routes, document_routes
from app.core.aligner import HybridAligner
from app.core.dict_manager import MongoDictManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# 全局变量，用于存储应用实例
_app_context = {"aligner": None, "mongo_dict_manager": None}

# ============================================================================
# 应用生命周期事件
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - startup: 初始化HybridAligner和DocumentService
    - shutdown: 清理资源
    """
    # ===== 启动 =====
    logger.info("🚀 应用启动中...")
    
    mongo_dict_manager = None
    try:
        # 初始化MongoDB字典管理器
        mongo_dict_manager = MongoDictManager()
        success, error_msg = mongo_dict_manager.init_mongo_conn(
            host=settings.MONGO_HOST,
            port=settings.MONGO_PORT,
            db_name=settings.MONGO_DB_NAME,
            username=settings.MONGO_USERNAME,
            password=settings.MONGO_PASSWORD
        )
        
        if not success:
            raise Exception(f"MongoDB连接失败: {error_msg}")
        
        logger.info("✅ MongoDB 字典管理器已初始化")
        _app_context["mongo_dict_manager"] = mongo_dict_manager
        
        # 初始化 HybridAligner（对齐逻辑内部通过路由传入 MongoDictManager）
        aligner = HybridAligner()
        _app_context["aligner"] = aligner
        logger.info("✅ HybridAligner 已初始化")
        
        # 初始化DocumentService（绑定到全局任务路由）
        document_routes.init_document_service(aligner)
        logger.info("✅ DocumentService 已初始化")
        
        logger.info("✅ 所有服务初始化完成！")
    
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {str(e)}", exc_info=True)
        raise
    
    yield  # 应用运行
    
    # ===== 关闭 =====
    logger.info("🛑 应用关闭中...")
    try:
        # 关闭MongoDB连接
        if mongo_dict_manager:
            mongo_dict_manager.db_service.disconnect()
            logger.info("✅ MongoDB 连接已关闭")
    except Exception as e:
        logger.error(f"❌ 清理资源失败: {str(e)}", exc_info=True)
    
    logger.info("✅ 应用已关闭")


# ============================================================================
# 创建FastAPI应用
# ============================================================================

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(dict_routes.router)
app.include_router(align_routes.router)
app.include_router(document_routes.router)


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "message": "服务运行正常"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式，自动重载
        log_level="info"
    )

