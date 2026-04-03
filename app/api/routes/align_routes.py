"""
对齐服务接口路由
"""

from fastapi import APIRouter, UploadFile, File, Form
import tempfile
import os
from app.api.schemas.align_schemas import (
    InitAlgorithmRequest,
    SingleTextAlignRequest,
    SetThresholdRequest,
    BatchTextAlignRequest,
    EntityCorrectionRequest,
)
from app.api.schemas.common import StandardResponse
from app.core.aligner import HybridAligner
from app.core.document_parser import DocumentParser
from app.core.dict_manager import MongoDictManager
from app.utils.logger import setup_logger
from app.utils.file_parser import parse_file

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/align", tags=["对齐服务"])

# 全局对齐器实例
aligner = HybridAligner()
dict_manager = MongoDictManager()
document_parser = DocumentParser()


@router.post("/init", response_model=StandardResponse)
async def init_algorithm(request: InitAlgorithmRequest):
    """
    初始化对齐算法
    
    - **bert_model_path**: BERT 模型路径（可选）
    - **levenshtein_thresh**: 模糊匹配阈值（可选）
    - **semantic_thresh**: 语义匹配阈值（可选）
    """
    try:
        success, error_msg = aligner.init_algorithm(
            bert_model_path=request.bert_model_path,
            levenshtein_thresh=request.levenshtein_thresh,
            semantic_thresh=request.semantic_thresh
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="算法初始化成功",
                data={"success": True}
            )
        else:
            return StandardResponse(
                code=500,
                msg=error_msg or "算法初始化失败",
                data={"success": False, "error_msg": error_msg}
            )
    except Exception as e:
        logger.error(f"初始化算法异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"初始化失败: {str(e)}",
            data={"success": False, "error_msg": str(e)}
        )


@router.post("/single-text", response_model=StandardResponse)
async def single_text_align(request: SingleTextAlignRequest):
    """
    单文本对齐
    
    - **text_chunk**: 文本片段（包含 text, language，默认中英文混合模式）
    - **entity_categories**: 要匹配的实体类别列表
    """
    try:
        # 1. 参数校验
        text_chunk = request.text_chunk
        if not text_chunk.text:
            return StandardResponse(
                code=400,
                msg="文本内容不能为空",
                data={"align_result": [], "process_time": 0}
            )
        
        
        entity_categories = request.entity_categories or ["apt", "tool", "vuln"]
        
        # 2. 调用 aligner.single_text_align()
        results, process_time = aligner.single_text_align(
            text_chunk=text_chunk.model_dump(),
            mongo_dict_manager=dict_manager,
            entity_categories=entity_categories
        )
        
        # 3. 返回 StandardResponse 格式
        response_data = {
            "align_result": results,
            "process_time": round(process_time, 3)
        }
        logger.info(f"单文本对齐返回结果: {len(results)} 个匹配, 处理时间: {round(process_time, 3)}秒")
        logger.debug(f"详细结果: {response_data}")

        return StandardResponse(
            code=200,
            msg="对齐完成",
            data=response_data
        )
    except Exception as e:
        logger.error(f"单文本对齐异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"对齐失败: {str(e)}",
            data={"align_result": [], "process_time": 0}
        )


@router.put("/set-threshold", response_model=StandardResponse)
async def set_threshold(request: SetThresholdRequest):
    """
    动态调整匹配阈值
    
    - **levenshtein_thresh**: 模糊匹配阈值（可选）
    - **semantic_thresh**: 语义匹配阈值（可选）
    """
    try:
        # 1. 参数校验（在 aligner.set_threshold 中已校验）
        # 2. 调用 aligner.set_threshold()
        success = aligner.set_threshold(
            levenshtein_thresh=request.levenshtein_thresh,
            semantic_thresh=request.semantic_thresh
        )
        
        if success:
            return StandardResponse(
                code=200,
                msg="阈值设置成功",
                data={"success": True}
            )
        else:
            return StandardResponse(
                code=400,
                msg="阈值设置失败，请检查阈值范围（0-1）",
                data={"success": False}
            )
    except Exception as e:
        logger.error(f"设置阈值异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"设置失败: {str(e)}",
            data={"success": False}
        )


@router.post("/batch-text", response_model=StandardResponse)
async def batch_text_align(request: BatchTextAlignRequest):
    """
    批量文本对齐
    
    - **texts**: 文本片段列表
    - **entity_categories**: 要匹配的实体类别列表
    """
    try:
        if not request.texts:
            return StandardResponse(
                code=400,
                msg="文本列表不能为空",
                data={"results": [], "total_process_time": 0}
            )
        
        entity_categories = request.entity_categories or ["apt", "tool", "vuln"]
        
        import time
        start_time = time.time()
        results = []
        
        for idx, text_chunk in enumerate(request.texts):
            try:
                align_results, process_time = aligner.single_text_align(
                    text_chunk=text_chunk.model_dump(),
                    mongo_dict_manager=dict_manager,
                    entity_categories=entity_categories
                )
                results.append({
                    "index": idx,
                    "text": text_chunk.text[:100] + "..." if len(text_chunk.text) > 100 else text_chunk.text,
                    "align_result": align_results,
                    "process_time": round(process_time, 3)
                })
            except Exception as e:
                logger.error(f"处理第 {idx} 个文本失败: {str(e)}")
                results.append({
                    "index": idx,
                    "text": text_chunk.text[:100] + "..." if len(text_chunk.text) > 100 else text_chunk.text,
                    "align_result": [],
                    "process_time": 0,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        return StandardResponse(
            code=200,
            msg="批量对齐完成",
            data={
                "results": results,
                "total_process_time": round(total_time, 3)
            }
        )
    except Exception as e:
        logger.error(f"批量文本对齐异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"批量对齐失败: {str(e)}",
            data={"results": [], "total_process_time": 0}
        )


@router.post("/upload-file", response_model=StandardResponse)
async def upload_file_align(
    file: UploadFile = File(...),
    entity_categories: str = Form(None)
):
    """
    上传文件进行实体对齐

    统一上传接口，后端仅分两条处理路径：
    - JSON 路径：按结构化候选字段处理
    - TXT 路径：TXT/PDF/DOC/DOCX 统一提取为纯文本后按 TXT 逻辑处理

    Args:
        file: 上传的 JSON 或 TXT 文件
        entity_categories: 实体类别，用逗号分隔 (可选，默认: "apt,tool,vuln")
    """
    logger.info(
        f"[CALL] upload_file_align(filename={file.filename}, "
        f"entity_categories={entity_categories})"
    )
    try:
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        supported_file_types = ['.json', '.txt', '.pdf', '.doc', '.docx']
        if file_ext not in supported_file_types:
            return StandardResponse(
                code=400,
                msg="不支持的文件格式，仅支持 JSON/TXT/PDF/DOC/DOCX 格式",
                data={"align_result": [], "process_time": 0}
            )
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # 解析文件为统一文本（仅两种处理路径：json 或 txt）
            if file_ext in ['.json', '.txt']:
                # 沿用现有轻量解析，主要用于编码/JSON校验
                success, error_msg, texts = parse_file(tmp_path)
                if not success:
                    return StandardResponse(
                        code=400,
                        msg=error_msg or "文件解析失败",
                        data={"align_result": [], "process_time": 0}
                    )
            else:
                # PDF/DOC/DOCX 走文档解析器
                try:
                    extracted_text = document_parser.parse(tmp_path)
                    texts = [extracted_text] if extracted_text.strip() else []
                except Exception as e:
                    return StandardResponse(
                        code=400,
                        msg=f"文档解析失败: {str(e)}",
                        data={"align_result": [], "process_time": 0}
                    )
            
            # 解析实体类别参数
            if not entity_categories or not entity_categories.strip():
                categories = ["apt", "tool", "vuln"]  # 默认实体类别
            else:
                categories = [c.strip() for c in entity_categories.split(',') if c.strip()]
            if not categories:
                    categories = ["apt", "tool", "vuln"]  # 默认值

            logger.info(f"文件对齐使用实体类别: {categories}")
            
            import time
            start_time = time.time()
            all_results = []
            
            # 统一语言标签：仅区分 json 与 txt
            # 非 json（包括 txt/pdf/doc/docx）都视为 txt 路径
            file_ext = os.path.splitext(tmp_path)[1].lower()
            language_type = "json" if file_ext == ".json" else "txt"
            logger.info(f"文件类型: {file_ext}，处理模式: {language_type}模式，实体类别: {categories}")
            
            # text 来源修正：
            # - json: 传原始 JSON 字符串，确保 _preprocess_text 能识别为 JSON 路径
            # - txt-like: 传解析后的纯文本
            if file_ext == ".json":
                try:
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                except UnicodeDecodeError:
                    with open(tmp_path, 'r', encoding='gbk') as f:
                        raw_content = f.read()
            else:
                raw_content = texts[0] if texts else ""
                
            text_chunk = {"text": raw_content, "language": language_type}

            # 在统一上传处理阶段提前完成预处理，避免后续重复解析（尤其是 JSON）
            # 仍复用 aligner._preprocess_text，确保效果与原逻辑一致
            original_text, preprocessed_candidates = aligner._preprocess_text(
                text_chunk["text"],
                dict_manager,
                categories
            )
            logger.info(
                f"[CALL] upload_file_align.preprocess_done("
                f"original_len={len(original_text)}, candidates={len(preprocessed_candidates)})"
            )
            text_chunk["original_text"] = original_text
            text_chunk["candidates"] = preprocessed_candidates

            if text_chunk["text"].strip():
                align_results, process_time = aligner.single_text_align(
                    text_chunk=text_chunk,
                    mongo_dict_manager=dict_manager,
                    entity_categories=categories
                )
                all_results.extend(align_results)
                logger.info(f"文件匹配完成，找到 {len(align_results)} 个实体")
            else:
                logger.warning("文件内容为空，未找到可匹配文本")
                process_time = 0
            
            
            total_time = time.time() - start_time

            response_data = {
                "align_result": all_results,
                "process_time": round(total_time, 3),
                "total_texts": len(texts),
                "matched_entities": len(all_results),
                # 统一返回后端最终解析/预处理后的原文，供前端展示与高亮
                "original_text": text_chunk.get("original_text", text_chunk.get("text", ""))
            }
            logger.info(f"文件上传对齐返回结果: {len(all_results)} 个匹配, 处理时间: {round(total_time, 3)}秒, 实体类别: {categories}")
            logger.debug(f"详细结果: {response_data}")
            
            return StandardResponse(
                code=200,
                msg="文件对齐完成",
                data=response_data
            )
        finally:
            # 删除临时文件
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"文件上传对齐异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"文件处理失败: {str(e)}",
            data={"align_result": [], "process_time": 0}
        )


@router.post("/correct-entity", response_model=StandardResponse)
async def correct_entity(request: EntityCorrectionRequest):
    """
    人工修正实体对齐结果，并自动反馈至词典
    
    - **original_text**: 原始匹配文本
    - **corrected_entity_id**: 修正后的实体ID（如果为None，表示删除匹配）
    - **align_result_id**: 对齐结果ID（用于标识）
    """
    try:
        # 如果提供了修正后的实体ID，更新实体信息
        if request.corrected_entity_id:
            # 查询实体
            entity = None
            for entity_type in ["apt", "tool", "vuln"]:
                entities, _ = dict_manager.query_entity(
                    {"entity_id": request.corrected_entity_id},
                    entity_type
                )
                if entities:
                    entity = entities[0]
                    break
            
            if not entity:
                return StandardResponse(
                    code=404,
                    msg="未找到指定的实体",
                    data={"success": False}
                )
            
            # 检查是否需要添加到变体（根据请求参数决定）
            # 这里简化处理，总是添加到变体
            original_text = request.original_text.strip()
            en_variants = entity.get("en_variants", [])
            zh_variants = entity.get("zh_variants", [])
            
            # 判断是中文还是英文（简单判断）
            is_chinese = any('\u4e00' <= char <= '\u9fff' for char in original_text)
            
            updated = False
            if is_chinese:
                if original_text not in zh_variants:
                    zh_variants.append(original_text)
                    updated = True
            else:
                if original_text not in en_variants:
                    en_variants.append(original_text)
                    updated = True
            
            # 如果有更新，保存到词典
            if updated:
                entity_type_map = {"apt": "apt", "tool": "tool", "vuln": "vuln"}
                entity_type = None
                for et, collection in entity_type_map.items():
                    if entity.get("entity_id", "").startswith(et.upper()[:4]):
                        entity_type = et
                        break
                
                if entity_type:
                    update_data = {
                        "entity_id": request.corrected_entity_id,
                        "entity_data": {
                            "en_variants": en_variants,
                            "zh_variants": zh_variants
                        }
                    }
                    success, error_msg = dict_manager.update_entity(update_data, entity_type)
                    
                    if success:
                        logger.info(f"实体 {request.corrected_entity_id} 已更新变体: {original_text}")
                        return StandardResponse(
                            code=200,
                            msg="实体修正成功，已自动更新词典",
                            data={"success": True, "updated_entity": entity}
                        )
                    else:
                        return StandardResponse(
                            code=500,
                            msg=f"更新词典失败: {error_msg}",
                            data={"success": False}
                        )
        
        return StandardResponse(
            code=200,
            msg="修正完成",
            data={"success": True}
        )
    except Exception as e:
        logger.error(f"实体修正异常: {str(e)}")
        return StandardResponse(
            code=500,
            msg=f"修正失败: {str(e)}",
            data={"success": False}
        )

