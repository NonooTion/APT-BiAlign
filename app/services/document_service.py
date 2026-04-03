"""
文档处理服务 (DocumentService)
集成：文档解析 + 分词 + 匹配的完整流程编排
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.core.document_parser import DocumentParser
from app.core.tokenizer import TokenizerPipeline
from app.core.aligner import HybridAligner
from app.core.dict_manager import MongoDictManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentService:
    """
    文档处理服务
    
    功能：
    - 智能判断文件格式（JSON/TXT 保留现有方式，PDF/DOC/DOCX 使用新方式）
    - 文档解析
    - 分词和n-gram生成
    - 实体匹配
    """
    
    def __init__(self, aligner: HybridAligner):
        """
        初始化文档服务
        
        Args:
            aligner: HybridAligner实例（用于复用现有处理逻辑和匹配）
        """
        logger.info("[CALL] DocumentService.__init__()")
        self.parser = DocumentParser()
        self.tokenizer_pipeline = TokenizerPipeline()
        self.aligner = aligner
    
    def process_document(
        self, 
        file_path: str,
        mongo_dict_manager: Optional[MongoDictManager] = None,
        entity_categories: List[str] = None,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        智能文档处理
        
        根据文件格式自动选择处理方式：
        - JSON: 保留使用 aligner._preprocess_text() 的现有方式
        - TXT/PDF/DOC/DOCX: 统一使用 DocumentParser + TokenizerPipeline 的分词逻辑
        
        Args:
            file_path: 文件路径
            mongo_dict_manager: MongoDB字典管理器（可选，用于后续匹配）
            entity_categories: 实体类别列表
            min_confidence: 候选的最低置信度阈值
        
        Returns:
            处理结果字典
        """
        logger.info(
            f"[CALL] DocumentService.process_document(file_path={file_path}, "
            f"min_confidence={min_confidence})"
        )
        if entity_categories is None:
            entity_categories = ['apt', 'tool', 'vuln']
        
        # 验证文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件格式
        file_ext = Path(file_path).suffix.lower()
        file_format = self.parser.get_file_format(file_path)
        
        logger.info(f"处理文档: {file_path} (格式: {file_format})")
        
        # 智能路由：根据文件格式选择处理方式
        if file_ext == '.json':
            # 📌 JSON 保留现有方式
            logger.info(f"[{file_format.upper()}] 使用现有处理方式 (aligner._preprocess_text)")
            return self._process_with_existing_aligner(
                file_path,
                file_format,
                mongo_dict_manager,
                entity_categories
            )
        
        elif file_ext in ['.txt', '.pdf', '.doc', '.docx']:
            # 📌 非 JSON（TXT/PDF/DOC/DOCX）统一使用同一分词流程
            logger.info(f"[{file_format.upper()}] 使用新的处理方式 (DocumentParser + Tokenizer)")
            return self._process_with_new_pipeline(
                file_path,
                file_format,
                min_confidence
            )
        
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def _process_with_existing_aligner(
        self,
        file_path: str,
        file_format: str,
        mongo_dict_manager: Optional[MongoDictManager],
        entity_categories: List[str]
    ) -> Dict[str, Any]:
        """
        使用现有的aligner处理方式（仅 JSON）
        """
        logger.info(
            f"[CALL] DocumentService._process_with_existing_aligner(file_path={file_path}, "
            f"file_format={file_format})"
        )
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                file_content = f.read()
        
        # 调用现有的 aligner 预处理方法
        try:
            original_text, candidate_objects = self.aligner._preprocess_text(
                file_content,
                mongo_dict_manager,
                entity_categories
            )
        except Exception as e:
            logger.error(f"预处理文本失败: {str(e)}")
            original_text = file_content
            candidate_objects = []
        
        return {
            "file_path": file_path,
            "format": file_format.upper(),
            "method": "existing_aligner",
            "text": original_text,
            "candidates": candidate_objects,
            "total_candidates": len(candidate_objects)
        }
    
    def _process_with_new_pipeline(
        self,
        file_path: str,
        file_format: str,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        使用统一处理方式（TXT/PDF/DOC/DOCX）
        步骤：1. 解析 → 2. 分词 → 3. n-gram + 衰减
        """
        logger.info(
            f"[CALL] DocumentService._process_with_new_pipeline(file_path={file_path}, "
            f"file_format={file_format}, min_confidence={min_confidence})"
        )
        try:
            # 1️⃣ 解析文档
            logger.info(f"正在解析 {file_format} 文档...")
            text = self.parser.parse(file_path)
            logger.info(f"成功解析文档，文本长度: {len(text)} 字符")
            
            # 2️⃣ 分词和n-gram生成
            logger.info("正在进行分词和n-gram生成...")
            tokenize_result = self.tokenizer_pipeline.process(text)
            
            # 3️⃣ 过滤高置信度候选
            all_candidates = tokenize_result["all_candidates"]
            high_conf_candidates = [
                {
                    "text": c["text"],
                    "confidence": c["confidence"],
                    "level": c["level"],
                    "pos_sequence": c["pos_sequence"],
                    "has_structure_id": c["has_structure_id"],
                    "sentence_id": c.get("sentence_id"),
                    "ngram_size": c.get("ngram_size")
                }
                for c in all_candidates
                if c["confidence"] >= min_confidence
            ]
            
            logger.info(
                f"完成处理。总候选数: {len(all_candidates)}, "
                f"高置信度候选数(>={min_confidence}): {len(high_conf_candidates)}"
            )
            
            return {
                "file_path": file_path,
                "format": file_format.upper(),
                "method": "new_tokenizer_pipeline",
                "text": text,
                "candidates": high_conf_candidates,
                "total_candidates": len(all_candidates),
                "high_confidence_candidates": len(high_conf_candidates),
                "sentences": tokenize_result.get("sentences", []),
                "confidence_threshold": min_confidence
            }
        
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"处理文档时出错: {str(e)}")

