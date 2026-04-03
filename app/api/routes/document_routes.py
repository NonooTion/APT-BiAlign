"""
文档处理 API 路由
支持：文档解析、分词、实体匹配的统一接口
"""

from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
import os
import tempfile

from app.core.aligner import HybridAligner
from app.services.document_service import DocumentService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/document", tags=["document"])

# 全局变量：在main.py中初始化
_service: Optional[DocumentService] = None


def init_document_service(aligner: HybridAligner):
    """
    初始化文档服务
    
    在main.py的startup事件中调用
    
    Args:
        aligner: HybridAligner实例
    """
    global _service
    _service = DocumentService(aligner)
    logger.info("✅ DocumentService 已初始化")


def get_service() -> DocumentService:
    """获取DocumentService实例"""
    if _service is None:
        raise RuntimeError("DocumentService 未初始化，请先调用 init_document_service()")
    return _service


# ============================================================================
# Pydantic 响应模型
# ============================================================================

class CandidateItem(BaseModel):
    """候选词条"""
    text: str
    confidence: float
    level: Optional[str] = None
    pos_sequence: Optional[str] = None
    has_structure_id: Optional[bool] = None
    sentence_id: Optional[int] = None
    ngram_size: Optional[int] = None


class DocumentParseResponse(BaseModel):
    """文档解析响应"""
    file_path: str
    format: str
    text: str
    success: bool
    message: str


class DocumentTokenizeResponse(BaseModel):
    """文档分词响应"""
    file_path: str
    format: str
    method: str
    text: str
    total_candidates: int
    high_confidence_candidates: Optional[int] = None
    candidates: List[CandidateItem]
    confidence_threshold: Optional[float] = None
    success: bool
    message: str


class DocumentAlignResponse(BaseModel):
    """文档对齐响应"""
    file_path: str
    format: str
    text: str
    candidates: List[CandidateItem]
    total_candidates: int
    success: bool
    message: str


# ============================================================================
# API 端点
# ============================================================================

@router.post("/parse", response_model=DocumentParseResponse)
async def parse_document(
    file: UploadFile = File(...),
    entity_categories: Optional[str] = Form(None)
) -> DocumentParseResponse:
    """
    📄 解析文档
    
    仅提取文本，不进行分词
    
    支持格式: PDF, DOC, DOCX, TXT, JSON
    
    Args:
        file: 上传的文件
        entity_categories: 实体类别（逗号分隔，如 "apt,tool,vuln"）
    
    Returns:
        包含文档内容的响应
    """
    temp_file_path = None
    try:
        service = get_service()
        
        # 保存上传的文件到临时路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file_path = tmp.name
        
        logger.info(f"处理上传的文件: {file.filename}")
        
        # 解析文档
        result = service.process_document(
            file_path=temp_file_path,
            entity_categories=entity_categories.split(",") if entity_categories else None,
            min_confidence=0.0  # 解析模式下不过滤
        )
        
        return DocumentParseResponse(
            file_path=file.filename,
            format=result["format"],
            text=result["text"],
            success=True,
            message="文档已成功解析"
        )
    
    except Exception as e:
        logger.error(f"文档解析失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.post("/tokenize", response_model=DocumentTokenizeResponse)
async def tokenize_document(
    file: UploadFile = File(...),
    min_confidence: float = Form(0.5),
    entity_categories: Optional[str] = Form(None)
) -> DocumentTokenizeResponse:
    """
    🔤 文档分词和n-gram生成
    
    解析文档并进行分词、n-gram候选生成（包含通用词衰减）
    
    支持格式: PDF, DOC, DOCX, TXT, JSON
    
    Args:
        file: 上传的文件
        min_confidence: 候选的最低置信度阈值 (0.0-1.0)，默认 0.5
        entity_categories: 实体类别（逗号分隔）
    
    Returns:
        包含分词候选的响应
    """
    temp_file_path = None
    try:
        service = get_service()
        
        # 验证confidence参数
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("min_confidence 必须在 0.0 到 1.0 之间")
        
        # 保存上传的文件到临时路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file_path = tmp.name
        
        logger.info(f"处理上传的文件（分词模式）: {file.filename}")
        
        # 处理文档
        result = service.process_document(
            file_path=temp_file_path,
            entity_categories=entity_categories.split(",") if entity_categories else None,
            min_confidence=min_confidence
        )
        
        # 转换候选为响应格式
        candidates = [CandidateItem(**c) for c in result["candidates"]]
        
        return DocumentTokenizeResponse(
            file_path=file.filename,
            format=result["format"],
            method=result.get("method", "unknown"),
            text=result["text"],
            total_candidates=result.get("total_candidates", 0),
            high_confidence_candidates=result.get("high_confidence_candidates"),
            candidates=candidates,
            confidence_threshold=result.get("confidence_threshold"),
            success=True,
            message=f"成功提取 {len(candidates)} 个候选词条"
        )
    
    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"文档分词失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"文档分词失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.post("/align", response_model=DocumentAlignResponse)
async def align_document(
    file: UploadFile = File(...),
    min_confidence: float = Form(0.5),
    entity_categories: Optional[str] = Form(None)
) -> DocumentAlignResponse:
    """
    🎯 完整流程：文档解析 → 分词 → 实体匹配
    
    支持格式: PDF, DOC, DOCX, TXT, JSON
    
    Args:
        file: 上传的文件
        min_confidence: 候选的最低置信度阈值 (0.0-1.0)，默认 0.5
        entity_categories: 实体类别（逗号分隔）
    
    Returns:
        包含分词和匹配结果的响应
    """
    temp_file_path = None
    try:
        service = get_service()
        
        # 验证confidence参数
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("min_confidence 必须在 0.0 到 1.0 之间")
        
        # 保存上传的文件到临时路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file_path = tmp.name
        
        logger.info(f"处理上传的文件（完整流程）: {file.filename}")
        
        # 处理文档
        result = service.process_document(
            file_path=temp_file_path,
            entity_categories=entity_categories.split(",") if entity_categories else None,
            min_confidence=min_confidence
        )
        
        # 转换候选为响应格式
        candidates = [CandidateItem(**c) for c in result["candidates"]]
        
        return DocumentAlignResponse(
            file_path=file.filename,
            format=result["format"],
            text=result["text"],
            candidates=candidates,
            total_candidates=result.get("total_candidates", 0),
            success=True,
            message=f"成功处理文档，提取 {len(candidates)} 个候选实体"
        )
    
    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"文档处理失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.get("/health")
async def health_check():
    """
    ✅ 健康检查
    
    检查文档服务是否正常工作
    """
    try:
        service = get_service()
        return {
            "status": "healthy",
            "service": "document_service",
            "format_support": ["pdf", "doc", "docx", "txt", "json"]
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=503, detail="文档服务不可用")
