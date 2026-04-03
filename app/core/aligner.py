"""
混合对齐算法模块 (HybridAligner)
实现精确匹配、模糊匹配、语义匹配三层对齐逻辑
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import time
import re
from sentence_transformers import SentenceTransformer
import Levenshtein
import numpy as np
from app.core.dict_manager import MongoDictManager
from app.services.cache import cache_service
from app.config import settings
from app.utils.logger import setup_logger
from app.core.tokenizer import TokenizerPipeline

logger = setup_logger(__name__)


class HybridAligner:
    """混合对齐算法类"""
    
    # 通用干扰词表（用于模糊匹配去噪）
    IGNORE_WORDS = [
        # === APT相关 ===
        "apt", "organization", "group", "team", "threat", "actor", "gang", "cluster",
        "campaign", "operation", "activity", "network", "unit", "inc", "ltd", "corp", "corporation",
        # === 攻击工具相关 ===
        "tool", "malware", "backdoor", "trojan", "downloader", "ransomware", "rootkit",
        "loader", "dropper", "agent", "rat", "implant", "framework", "payload", "webshell",
        "botnet", "worm", "spyware", "adware", "keylogger", "exploit", "crypter", "virus",
        "utility", "utilities", "shell", "command", "script", "scripts", "powershell",
        # === 漏洞相关 ===
        "vulnerability", "vuln", "cve", "flaw", "bug", "issue", "weakness", "injection",
        "overflow", "rce", "remote code execution", "dos", "ddos", "bypass", "patch", "poc",
        "zero-day", "0day", "xss",
        # === 中文 ===
        "组织", "团队", "黑客", "攻击", "活动", "行动", "小组", "公司", "集团", "团伙",
        "工具", "恶意软件", "后门", "木马", "下载器", "勒索软件", "加载器", "释放器",
        "代理", "远控", "植入", "框架", "载荷", "蠕虫", "间谍软件", "漏洞", "利用",
        "缺陷", "错误", "补丁", "溢出", "注入", "跨站", "拒绝服务", "绕过", "提权", "执行",
        "键盘记录器", "利用工具", "植入物", "加密器", "病毒", "广告软件", "僵尸网络"
    ]

    # 通用类别词表（匹配前如果清洗结果在此列表中，则直接拦截，避免误报）
    GENERIC_TERMS = {
        # English
        "group", "team", "actor", "activity", "operation", "campaign",
        "downloader", "ransomware", "agent", "backdoor", "trojan", "webshell", "rootkit",
        "malware", "spyware", "loader", "dropper", "worm", "botnet",
        "exploit", "payload", "implant", "virus", "rat", "framework",
        "vulnerability", "vuln", "zero-day", "0day", "bug", "flaw", "issue", "patch",
        "powershell", "script", "scripts", "utility", "shell", "command",
        # APT命名常用泛指词
        "panda", "bear", "dragon", "tiger", "spider", "kitten", "eagle", "wolf",
        "lotus", "ocean", "dark", "shadow", "phantom", "ghost", "cyber", "chollima",
        # Chinese
        "组织", "团队", "黑客", "攻击", "小组", "团伙",
        "下载器", "勒索软件", "代理", "后门", "木马", "恶意软件", "加载器", "病毒",
        "漏洞", "工具", "载荷", "脚本", "工具包", "框架", "补丁",
        # APT命名常用中文泛指词
        "熊猫", "龙", "虎", "莲花", "海洋", "幽灵", "影子", "千里马"
    }
    
    # 结构化编号模式（用于编号检查）
    STRUCTURED_PATTERNS = [
        r'APT-?[A-Z]-?\d+',      # APT-C-27, APT-Q-36
        r'APT[-_]?\d+',          # APT28, APT-28, APT_28
        r'TA-?\d+',              # TA-505
        r'TAG-?\d+',             # TAG-38
        r'UNC\d+',               # UNC2596
        r'FIN\d+',               # FIN7
        r'CVE-\d{4}-\d+',        # CVE
        r'MS\d{2}-\d{3}'         # MS Bulletin
    ]

    def __init__(self):
        self.bert_model: Optional[SentenceTransformer] = None
        self.levenshtein_threshold: float = settings.LEVENSHTEIN_THRESHOLD
        self.semantic_threshold: float = settings.SEMANTIC_THRESHOLD
        self._model_loaded = False
        # 位置占用追踪（用于 _find_text_position）
        self.used_positions: Set[int] = set()
        # 复用 demo 同款分词/分句/n-gram pipeline（用于非 JSON 文本候选生成）
        self.tokenizer_pipeline = TokenizerPipeline()
    
    def _clean_noise(self, text: str) -> str:
        """
        去除干扰词（增强版：保护结构化ID）
        
        Args:
            text: 原始文本
        
        Returns:
            去噪后的文本
        """
        if not text:
            return ""
        
        # 1. 提取并保护结构化ID
        # 避免像 "APT28" 中的 "APT" 被当做干扰词删除，变成 "28"
        protected_text = text
        placeholders = {}
        counter = 0
        
        # 扩展保护模式，确保覆盖常见ID格式
        protection_patterns = self.STRUCTURED_PATTERNS + [
            r'[A-Z]+\d+',  # 宽泛的 字母+数字 组合
        ]
        
        for pattern in protection_patterns:
            # 使用回调函数进行替换，确保每个匹配项都有唯一占位符
            def replace_callback(match):
                nonlocal counter
                matched_str = match.group(0)
                placeholder = f"__PROTECTED_ID_{counter}__"
                placeholders[placeholder] = matched_str
                counter += 1
                return placeholder
                
            protected_text = re.sub(pattern, replace_callback, protected_text, flags=re.IGNORECASE)
            
        # 2. 统一转小写进行清洗
        cleaned = protected_text.lower()
        
        # 将干扰词按长度降序排序，长词优先匹配
        sorted_ignore_words = sorted(self.IGNORE_WORDS, key=len, reverse=True)
        
        # 3. 移除干扰词
        for word in sorted_ignore_words:
            word_lower = word.lower()
            
            # 判断是否为纯英文/数字
            if re.match(r'^[a-z0-9\s\-]+$', word_lower):
                # 英文逻辑：使用正则表达式确保单词独立性
                # (?<![a-z0-9]) 确保前面不是英文字符或数字
                # (?![a-z0-9]) 确保后面不是英文字符或数字
                pattern = rf'(?<![a-z0-9]){re.escape(word_lower)}(?![a-z0-9])'
                cleaned = re.sub(pattern, "", cleaned)
            else:
                # 中文或混合逻辑：直接替换
                cleaned = cleaned.replace(word_lower, "")
        
        # 4. 恢复结构化ID（保持原样，不转小写）
        for placeholder, original in placeholders.items():
            # 注意：cleaned已经是小写了，但placeholder是特殊的，不会被转小写影响（因为包含下划线和大写）
            # 我们将placeholder替换回original
            cleaned = cleaned.replace(placeholder.lower(), original)
        
        # 5. 去除多余空格和特殊字符残留
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def _is_generic_term(self, text: str) -> bool:
        """
        判断是否为通用词（宽泛的类别词）
        
        如果一个候选词在移除干扰因素后，其核心部分为空或者本身就是一个通用类别词，则不应参与模糊/语义匹配。
        
        Args:
            text: 待检测的文本
            
        Returns:
            bool: 是否为通用词
        """
        if not text:
            return True
            
        # 1. 基础清洗（移除可能的干扰）
        cleaned = self._clean_noise(text)
        
        # 2. 如果清洗完变成了空字符串，说明全是干扰词/通用词
        if not cleaned:
            return True
        
        # 3. 判断清洗后的核心部分是否在通用词表中
        if cleaned in self.GENERIC_TERMS:
            return True
            
        # 4. 针对长度极短的纯数字或无意义字符的额外检查
        if len(cleaned) < 2:
            return True
            
        return False
    
    def _extract_structured_id(self, text: str) -> Optional[str]:
        """
        提取结构化编号
        
        Args:
            text: 待检测的文本
            
        Returns:
            结构化编号（大写标准化），或None
        """
        for pattern in self.STRUCTURED_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).upper()
        return None
    
    def _check_id_compatible(self, candidate: str, entity_str: str) -> bool:
        """
        检查编号是否兼容（用于模糊匹配阶段）
        
        Args:
            candidate: 候选字符串
            entity_str: 实体字符串
            
        Returns:
            True = 兼容，允许继续匹配
            False = 不兼容，跳过该实体
        """
        cand_id = self._extract_structured_id(candidate)
        entity_id = self._extract_structured_id(entity_str)
        
        # 都没有编号 → 兼容
        if not cand_id and not entity_id:
            return True
        
        # 只有一方有编号 → 兼容（如"黄金鼠"→"APT-C-27"）
        if not cand_id or not entity_id:
            return True
        
        # 都有编号 → 必须相同
        return cand_id == entity_id
    
    def _find_text_position(self, text: str, matched_text: str) -> Tuple:
        """
        在原文中查找匹配文本的位置（不区分大小写），支持位置追踪避免重复
        
        Args:
            text: 原文
            matched_text: 要查找的文本
            
        Returns:
            (start_pos, end_pos) 或 (-1, -1) 如果未找到
        """
        if not text or not matched_text:
            return (-1, -1)
        
        lower_text = text.lower()
        lower_match = matched_text.lower()
        
        # 查找所有出现位置，返回第一个未被使用的位置
        start = 0
        while True:
            pos = lower_text.find(lower_match, start)
            if pos == -1:
                # 所有位置都已使用或未找到
                return (-1, -1)
            
            end = pos + len(matched_text)
            
            # 检查此位置是否已被使用（检查是否有任何字符重叠）
            occupied = False
            for i in range(pos, end):
                if i in self.used_positions:
                    occupied = True
                    break
            
            if not occupied:
                # 找到未使用的位置，标记为已使用
                for i in range(pos, end):
                    self.used_positions.add(i)
                
                # 调试验证：检查位置是否正确
                actual_slice = text[pos:end]
                if actual_slice.lower() != matched_text.lower():
                    logger.error(f"位置计算错误！预期: {matched_text}, 实际切片: {actual_slice} (Pos: {pos}-{end})")
                else:
                    # 记录成功的匹配（用于调试）
                    logger.debug(f"位置查找成功: '{matched_text}' -> 位置 {pos}-{end}, 实际文本: '{actual_slice}'")
                
                return (pos, end)
            
            # 继续查找下一个出现位置
            start = pos + 1
        
        return (-1, -1)
    

    
    def init_algorithm(
        self,
        bert_model_path: Optional[str] = None,
        levenshtein_thresh: Optional[float] = None,
        semantic_thresh: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        初始化算法
        
        Args:
            bert_model_path: Sentence-BERT 模型路径
            levenshtein_thresh: 模糊匹配阈值
            semantic_thresh: 语义匹配阈值
        
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 设置匹配阈值
            if levenshtein_thresh is not None:
                if not 0 <= levenshtein_thresh <= 1:
                    return False, "模糊匹配阈值必须在 0-1 之间"
                self.levenshtein_threshold = levenshtein_thresh
            
            if semantic_thresh is not None:
                if not 0 <= semantic_thresh <= 1:
                    return False, "语义匹配阈值必须在 0-1 之间"
                self.semantic_threshold = semantic_thresh
            
            # 加载 Sentence-BERT 模型
            model_path = bert_model_path or settings.BERT_MODEL_PATH
            
            try:
                logger.info(f"正在加载 Sentence-BERT 模型: {model_path}")
                self.bert_model = SentenceTransformer(model_path)
                self._model_loaded = True
                logger.info("Sentence-BERT 模型加载成功")
            except Exception as e:
                error_msg = f"加载 BERT 模型失败: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
            return True, None
            
        except Exception as e:
            error_msg = f"初始化算法失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def single_text_align(
        self,
        text_chunk: Dict[str, Any],
        mongo_dict_manager: MongoDictManager,
        entity_categories: List[str] = ["apt", "tool", "vuln"]
    ) -> Tuple[List[Dict], float]:
        """
        对单个文本片段进行实体对齐
        
        Args:
            text_chunk: 文本片段字典，包含"text"字段
            mongo_dict_manager: 词典管理器实例
            entity_categories: 要匹配的实体类别列表
        
        Returns:
            (对齐结果列表, 处理耗时（秒）)
        """
        import time
        start_time = time.time()
        
        # 重置位置追踪（确保每次对齐都从干净状态开始）
        self.used_positions = set()
        
        # 记录接收到的实体类别参数
        logger.info(f"单文本对齐开始，实体类别: {entity_categories}")
        logger.info(
            f"[CALL] single_text_align(text_len={len(str(text_chunk.get('text', '')))}, "
            f"has_preprocessed={'original_text' in text_chunk and 'candidates' in text_chunk})"
        )
        
        try:
            # 1. 提取文本并进行分词预处理
            # 支持两种输入：
            # A) 常规输入：仅包含 text（在此函数内部执行 _preprocess_text）
            # B) 预处理输入：已包含 original_text + candidates（跳过重复预处理）
            preprocessed_original_text = text_chunk.get("original_text")
            preprocessed_candidates = text_chunk.get("candidates")

            if (
                isinstance(preprocessed_original_text, str)
                and isinstance(preprocessed_candidates, list)
            ):
                original_text = preprocessed_original_text
                candidates = preprocessed_candidates
                logger.info(
                    f"使用预处理输入，跳过 _preprocess_text，候选数: {len(candidates)}"
                )
            else:
                text = text_chunk.get("text", "")
                if not text:
                    return [], 0.0
                # 提取原文和候选列表
                original_text, candidates = self._preprocess_text(text, mongo_dict_manager, entity_categories)

            if not candidates:
                logger.info("未提取到候选字符串")
                return [], time.time() - start_time
            
            logger.info(f"文本分词提取了 {len(candidates)} 个候选字符串")
            # 打印前若干个候选，便于调试观察“分词/候选”效果
            max_preview = 20
            preview_candidates = candidates[:max_preview]
            for idx, cand in enumerate(preview_candidates, start=1):
                logger.info(
                    f"[候选][{idx}/{len(candidates)}] text='{cand['text']}', "
                    f"start_pos={cand['start_pos']}, end_pos={cand['end_pos']}"
                )
            if len(candidates) > max_preview:
                logger.info(f"... 其余 {len(candidates) - max_preview} 个候选已省略")

            
            # 3. 按优先级执行匹配（不短路，确保所有候选都能被尝试匹配）
            final_results = []
            matched_candidates = set()
            
            # 3.1 精确匹配（最高优先级）
            exact_results, matched_candidates = self.exact_match(
                candidates,
                mongo_dict_manager,
                entity_categories,
                original_text
            )
            final_results.extend(exact_results)
            logger.info(f"精确匹配找到 {len(exact_results)} 个实体，已匹配候选数: {len(matched_candidates)}")
            
            # 3.2 模糊匹配（对未匹配的候选进行）
            fuzzy_results, matched_candidates, blocked_candidates = self.fuzzy_match(
                candidates,
                matched_candidates,
                mongo_dict_manager,
                entity_categories,
                original_text
            )
            final_results.extend(fuzzy_results)
            logger.info(f"模糊匹配找到 {len(fuzzy_results)} 个实体，累计已匹配候选数: {len(matched_candidates)}, blocked候选: {len(blocked_candidates)}")
            
            # 3.3 语义匹配（对仍未匹配的候选进行，排除blocked候选）
            semantic_results, matched_candidates = self.semantic_match(
                candidates,
                matched_candidates | blocked_candidates,  # 合并排除blocked候选
                mongo_dict_manager,
                entity_categories,
                original_text
            )
            final_results.extend(semantic_results)
            logger.info(f"语义匹配找到 {len(semantic_results)} 个实体，最终已匹配候选数: {len(matched_candidates)}")

            # 4. 为未匹配的候选添加"fail"结果
            # 注意：需重新计算真正匹配成功的候选集合（排除blocked候选）
            # blocked候选虽然在semantic_match中被标记为matched以跳过计算，但它们没有生成结果，应视为fail
            actually_matched_texts = {
                res["matched_text"] 
                for res in final_results 
                if res["match_type"] != "fail"
            }
            
            unmatched_candidate_objs = [c for c in candidates if c["text"] not in actually_matched_texts]

            for candidate_obj in unmatched_candidate_objs:
                # 直接使用候选对象的位置信息
                fail_result = {
                    "entity_id": None,
                    "entity_type": None,
                    "en_core": None,
                    "zh_core": None,
                    "match_type": "fail",
                    "confidence": 1.0,
                    "matched_text": candidate_obj["text"],
                    "matched_field": None,
                    "start_pos": candidate_obj["start_pos"],
                    "end_pos": candidate_obj["end_pos"]
                }
                final_results.append(fail_result)

            if unmatched_candidate_objs:
                logger.info(f"为 {len(unmatched_candidate_objs)} 个未匹配候选字符串添加了'fail'结果")

            # 5. 计算处理耗时
            process_time = time.time() - start_time

            # 打印每个候选的最终匹配结果（包括 fail），便于端到端调试
            for res in final_results:
                logger.info(
                    "[匹配结果] matched_text='%s', match_type=%s, "
                    "entity_id=%s, entity_type=%s, en_core='%s', zh_core='%s', confidence=%.4f, "
                    "start_pos=%s, end_pos=%s",
                    res.get("matched_text"),
                    res.get("match_type"),
                    res.get("entity_id"),
                    res.get("entity_type"),
                    res.get("en_core"),
                    res.get("zh_core"),
                    float(res.get("confidence", 0.0)),
                    res.get("start_pos"),
                    res.get("end_pos"),
                )

            logger.info(f"对齐完成：找到 {len(final_results)} 个结果（其中 {len(unmatched_candidate_objs)} 个失败），耗时 {process_time:.2f} 秒")

            return final_results, process_time
            
        except Exception as e:
            error_msg = f"单文本对齐失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [], time.time() - start_time
    
    def exact_match(
        self,
        candidates: List[Dict],  # 候选对象列表
        mongo_dict_manager: MongoDictManager,
        entity_categories: List[str],
        original_text: str = ""  # 保留但不使用
    ) -> Tuple[List[Dict], Set[str]]:
        """
        精确匹配
        
        Args:
            candidates: 候选对象列表 [{"text": str, "start_pos": int, "end_pos": int}, ...]
            mongo_dict_manager: 词典管理器实例
            entity_categories: 实体类别列表
        
        Returns:
            (匹配结果列表, 已匹配的候选字符串集合)
        """
        logger.debug(f"精确匹配开始，实体类别: {entity_categories}, 候选数量: {len(candidates)}")
        results = []
        matched_candidates = set()
        # 本地缓存查询结果，避免重复查询相同文本
        # 结构: text -> list of (entity, entity_type)
        query_cache = {}
        
        for candidate in candidates:
            cand_text = candidate["text"]
            cand_text_stripped = cand_text.strip()
            
            if not cand_text_stripped:
                continue
                
            # 1. 获取匹配实体（优先查缓存，否则查库）
            if cand_text_stripped in query_cache:
                found_entities = query_cache[cand_text_stripped]
            else:
                found_entities = []
                import re
                try:
                    escaped_candidate = re.escape(cand_text_stripped)
                    exact_pattern = f"^{escaped_candidate}$"
                    
                    query_conditions = [
                        {"en_core": {"$regex": exact_pattern, "$options": "i"}},
                        {"zh_core": {"$regex": exact_pattern, "$options": "i"}},
                        {"en_variants": {"$regex": exact_pattern, "$options": "i"}},
                        {"zh_variants": {"$regex": exact_pattern, "$options": "i"}}
                    ]
                    query_params = {"$or": query_conditions}
                    
                    # 对每个实体类别进行查询
                    for entity_type in entity_categories:
                        collection_name = {
                            "apt": "apt_organizations",
                            "tool": "attack_tools",
                            "vuln": "vulnerabilities"
                        }.get(entity_type)
                        
                        if not collection_name:
                            continue
                        
                        collection = mongo_dict_manager.db_service.get_collection(collection_name)
                        if collection is None:
                            continue
                        
                        matched_in_coll = list(collection.find(query_params))
                        for ent in matched_in_coll:
                            found_entities.append((ent, entity_type))
                except Exception as e:
                    logger.error(f"精确匹配查询出错 ({cand_text_stripped}): {str(e)}")
                    found_entities = []
                
                # 存入缓存
                query_cache[cand_text_stripped] = found_entities

            # 2. 为当前候选对象生成结果
            if not found_entities:
                continue

            # 新增：如果有多个匹配实体，只保留一个“最佳”匹配
            # 优先级：核心名称完全匹配 > 其它（默认按数据库返回顺序）
            if len(found_entities) > 1:
                # 定义排序键：如果是核心名称匹配，优先级更高(0)，否则(1)
                def sort_key(item):
                    ent, _ = item
                    cand_lower = cand_text_stripped.lower()
                    is_core = (ent.get("en_core", "").lower() == cand_lower) or \
                              (ent.get("zh_core", "").lower() == cand_lower)
                    return 0 if is_core else 1
                
                found_entities.sort(key=sort_key)
                found_entities = found_entities[:1]  # 只取第一个

            for entity, entity_type in found_entities:
                # 确定匹配的字段（大小写不敏感）
                matched_field = None
                candidate_lower = cand_text_stripped.lower()
                if entity.get("en_core", "").lower() == candidate_lower:
                    matched_field = "en_core"
                elif entity.get("zh_core", "").lower() == candidate_lower:
                    matched_field = "zh_core"
                elif candidate_lower in [v.lower() for v in entity.get("en_variants", [])]:
                    matched_field = "en_variants"
                elif candidate_lower in [v.lower() for v in entity.get("zh_variants", [])]:
                    matched_field = "zh_variants"
                
                # 直接使用候选对象的位置信息
                result = {
                    "entity_id": entity.get("entity_id"),
                    "entity_type": entity_type,
                    "en_core": entity.get("en_core", ""),
                    "zh_core": entity.get("zh_core", ""),
                    "match_type": "exact",
                    "confidence": 1.0,
                    "matched_text": cand_text,
                    "matched_field": matched_field,
                    "start_pos": candidate["start_pos"],
                    "end_pos": candidate["end_pos"]
                }
                results.append(result)
                matched_candidates.add(cand_text)
        
        logger.info(f"精确匹配找到 {len(results)} 个结果")
        return results, matched_candidates
    
    def fuzzy_match(
        self,
        candidates: List[Dict],  # 候选对象列表
        matched_candidates: Set[str],
        mongo_dict_manager: MongoDictManager,
        entity_categories: List[str],
        original_text: str = ""  # 保留但不使用
    ) -> Tuple[List[Dict], Set[str], Set[str]]:
        """
        模糊匹配
        
        Args:
            candidates: 候选对象列表 [{"text": str, "start_pos": int, "end_pos": int}, ...]
            matched_candidates: 已匹配的候选字符串集合（避免重复匹配）
            mongo_dict_manager: 词典管理器实例
            entity_categories: 实体类别列表
        
        Returns:
            (匹配结果列表, 已匹配的候选字符串集合, blocked候选集合)
        """
        logger.debug(f"模糊匹配开始，实体类别: {entity_categories}, 候选数量: {len(candidates)}, 已匹配: {len(matched_candidates)}")
        results = []
        current_matched_candidates = matched_candidates.copy()
        # 记录传入的已匹配集合，用于跳过previous stages已匹配的项
        passed_in_matched = matched_candidates.copy()
        
        # 新增：记录被编号规则阻止的候选
        blocked_candidates = set()
        
        # 本地缓存模糊匹配计算结果
        # 结构: text -> (best_match, best_similarity, has_structured_id)
        fuzzy_calc_cache = {}
        
        for candidate_obj in candidates:
            cand_text = candidate_obj["text"]
            
            # 如果是exact_match已经匹配过的，直接跳过
            if cand_text in passed_in_matched:
                continue
            
            cand_text_stripped = cand_text.strip()
            if not cand_text_stripped or len(cand_text_stripped) < 2:
                continue
            
            # 拦截通用词
            if self._is_generic_term(cand_text_stripped):
                logger.debug(f"模糊匹配拦截通用词: '{cand_text_stripped}'")
                continue

            # --- 1. 获取/执行模糊匹配计算 (带缓存) ---
            if cand_text_stripped in fuzzy_calc_cache:
                best_match, best_similarity, has_structured_id = fuzzy_calc_cache[cand_text_stripped]
                found_match = (best_match is not None and best_similarity >= self.levenshtein_threshold)
            else:
                # 执行计算
                best_match, best_similarity, has_structured_id = self._calculate_fuzzy_single(
                    cand_text_stripped, entity_categories, mongo_dict_manager
                )
                # 存入缓存
                fuzzy_calc_cache[cand_text_stripped] = (best_match, best_similarity, has_structured_id)
                found_match = (best_match is not None and best_similarity >= self.levenshtein_threshold)

            # --- 2. 生成结果 (如果找到匹配) ---
            if found_match:
                entity = best_match["entity"]
                result = {
                    "entity_id": entity.get("entity_id"),
                    "entity_type": best_match["entity_type"],
                    "en_core": entity.get("en_core", ""),
                    "zh_core": entity.get("zh_core", ""),
                    "match_type": "fuzzy",
                    "confidence": round(best_similarity, 4),
                    "matched_text": cand_text,
                    "matched_field": best_match["matched_string"],
                    "start_pos": candidate_obj["start_pos"],
                    "end_pos": candidate_obj["end_pos"]
                }
                results.append(result)
                current_matched_candidates.add(cand_text)

            # 新增：如果候选含编号但未匹配成功，记录为blocked
            if has_structured_id and not found_match:
                blocked_candidates.add(cand_text)
                logger.debug(f"含编号但未匹配，加入blocked: {cand_text}")
        
        # 后处理：过滤结构化数字差异导致的误报
        results = self._filter_structural_mismatches(results)
        logger.info(f"模糊匹配后处理：过滤前 {len(results) + len([r for r in results if self._has_structural_number_diff(r['matched_text'], r['matched_field'])])} 条，过滤后 {len(results)} 条")
        
        return results, current_matched_candidates, blocked_candidates

    def _build_char_ngram_queries(self, candidate: str, n=3, max_word_length=100, max_pattern_length=1000) -> List[Dict]:
        """
        对英文候选进行字符级N-gram切分并生成查询（动态N值优化版）
        
        Args:
            candidate: 候选文本
            n: 默认基础N值（此版本中将被动态逻辑覆盖）
            max_word_length: 最大单词长度
            max_pattern_length: 单个正则最大长度
        
        Returns:
            查询列表
        """
        # 1. 分词与清洗
        # 替换常见标点为空格
        cleaned = re.sub(r'[()（）\[\]【】{}「」,，]', ' ', candidate)
        words = cleaned.split()
        
        # 2. 动态生成N-gram
        all_ngrams = []
        for w in words:
            # 跳过超长单词（避免对哈希值等进行处理）
            w_len = len(w)
            if w_len > max_word_length:
                logger.debug(f"跳过超长单词: {w[:20]}...")
                continue
                
            # 根据单词长度动态决定 N 值
            current_n = 3
            if w_len <= 6:
                current_n = 3
            elif w_len <= 10:
                current_n = 4
            elif w_len <= 15:
                current_n = 5
            else:
                current_n = 6
                
            # 仅处理长度满足n-gram要求的单词
            if w_len >= current_n:
                char_ngrams = [w[i:i+current_n] for i in range(w_len - current_n + 1)]
                all_ngrams.extend(char_ngrams)
        
        unique_ngrams = list(set(all_ngrams))
        if not unique_ngrams:
            return []
            
        # 3. 构建正则查询（分批处理）
        queries = []
        batch_size = 10  # 每批处理10个n-gram
        escaped_ngrams = [re.escape(ng) for ng in unique_ngrams]
        
        for i in range(0, len(escaped_ngrams), batch_size):
            batch = escaped_ngrams[i:i+batch_size]
            pattern = '|'.join(batch)
            
            if len(pattern) > max_pattern_length:
                continue
            
            query = {
                "$or": [
                    {"en_core": {"$regex": pattern, "$options": "i"}},
                    {"zh_core": {"$regex": pattern, "$options": "i"}},
                    {"en_variants": {"$regex": pattern, "$options": "i"}},
                    {"zh_variants": {"$regex": pattern, "$options": "i"}}
                ]
            }
            queries.append(query)
            
        return queries

    def _safe_query_with_fallback(self, collection, queries: List[Dict], cand_text: str) -> List[Dict]:
        """
        
        Args:
            collection: MongoDB集合
            queries: 查询列表
            cand_text: 候选文本
        
        Returns:
            查询结果列表
        """
        results = []
        
        # 执行N-gram查询
        for query in queries:
            try:
                matched = list(collection.find(query).limit(100))
                results.extend(matched)
            except Exception as e:
                logger.warning(f"模糊查询分片失败: {str(e)}")
                continue
        
        return results
    
    def _calculate_fuzzy_single(
        self, 
        cand_text: str, 
        entity_categories: List[str],
        mongo_dict_manager: MongoDictManager
    ) -> Tuple[Optional[Dict], float, bool]:
        """
        对单个候选字符串执行模糊匹配计算 (双层策略)
        Layer 1: 基于分词的正则匹配 (优先)
        Layer 2: N-gram 字符级模糊匹配 (托底)
        
        返回: (best_match, best_similarity, has_structured_id)
        """
        cand_text_stripped = cand_text.strip()
        has_structured_id = bool(self._extract_structured_id(cand_text_stripped))
        
        best_match = None
        best_similarity = 0.0
        
        # --- Layer 1: 基于分词的正则匹配 ---
        # 仅针对英文/混合文本启用 (含中文的继续走原有逻辑或视为Layer 1的一种特殊情况)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in cand_text_stripped)
        
        if not has_chinese:
            # 1.1 构建分词正则查询
            regex_query, valid_tokens = self._build_token_regex_query(cand_text_stripped)
            
            if regex_query:
                # 手动执行 Layer 1 查询
                potential_entities_l1 = []
                for entity_type in entity_categories:
                    collection_name = {
                        "apt": "apt_organizations",
                        "tool": "attack_tools",
                        "vuln": "vulnerabilities"
                    }.get(entity_type)
                    
                    if not collection_name:
                        continue
                        
                    collection = mongo_dict_manager.db_service.get_collection(collection_name)
                    if collection is None:
                        continue
                        
                    try:
                        # 使用正则查询
                        matched = list(collection.find(regex_query).limit(50))
                        for ent in matched:
                            potential_entities_l1.append((ent, entity_type))
                    except Exception as e:
                        logger.warning(f"Layer 1 正则查询失败: {e}")
                
                # 1.2 评估 Layer 1 结果
                if potential_entities_l1:
                    logger.debug(f"Layer 1 找到 {len(potential_entities_l1)} 个候选实体 (Input: {cand_text_stripped})")
                    
                for entity, entity_type in potential_entities_l1:
                    # 检查编号兼容性
                    entity_name = entity.get("en_core", "")
                    if has_structured_id:
                        if not self._check_id_compatible(cand_text_stripped, entity_name):
                            continue
                    
                    # 收集所有相关名称用于比对
                    names_to_check = [entity.get("en_core", ""), entity.get("zh_core", "")]
                    names_to_check.extend(entity.get("en_variants", []))
                    names_to_check.extend(entity.get("zh_variants", []))
                    names_to_check = [n for n in names_to_check if n]
                    
                    current_best_sim = 0.0
                    current_best_str = ""
                    
                    is_layer1_success = False
                    
                    for name in names_to_check:
                        name_clean = name.strip()
                        if not name_clean:
                            continue
                            
                        # 计算整体相似度
                        sim = Levenshtein.ratio(cand_text_stripped.lower(), name_clean.lower())
                        
                        if sim > current_best_sim:
                            current_best_sim = sim
                            current_best_str = name_clean
                            
                        # Condition A: Token Exact Match
                        # 候选实体的名称与任意一个保留分词完全一致
                        # 需忽略大小写
                        for token in valid_tokens:
                            if token.lower() == name_clean.lower():
                                is_layer1_success = True
                                current_best_sim = 0.95 # 强制置信度 1
                                break
                        
                        if is_layer1_success:
                            break
                            
                    # Condition B: Whole Sentence Similarity > Threshold
                    if not is_layer1_success and current_best_sim >= self.levenshtein_threshold:
                         is_layer1_success = True
                    
                    if is_layer1_success:
                        if current_best_sim > best_similarity:
                            best_similarity = current_best_sim
                            best_match = {
                                "entity": entity,
                                "entity_type": entity_type,
                                "matched_string": current_best_str
                            }
                
                # 如果 Layer 1 成功找到匹配，直接返回
                if best_match:
                    logger.debug(f"Layer 1 匹配成功: {cand_text_stripped} -> {best_match['matched_string']} (Conf: {best_similarity})")
                    return best_match, best_similarity, has_structured_id

        # --- Layer 2: N-gram 托底 (原有逻辑) ---
        # 如果 Layer 1 未执行(中文) 或 未找到结果，执行此逻辑
        
        ngram_queries = []
        regex_query = None # 仅用于中文
        
        if has_chinese:
             # 中文逻辑：原有正则策略
            try:
                # 去空格降低 unique chars 数与正则复杂度
                clean_no_ws = re.sub(r'\s+', '', cand_text_stripped)
                candidate_len = len(clean_no_ws)
                required_chars = (candidate_len * 3) // 4

                # 防止正则过大（Mongo 可能报：Regular expression is too large）
                max_unique_chars_for_regex = 40
                max_required_chars_for_regex = 25

                clean_candidate = re.sub(r'[()（）\[\]【】{}「」]', '', clean_no_ws)
                unique_chars = set(clean_candidate)
                escaped_chars = [re.escape(char) for char in unique_chars if char.strip()]
                char_class_pattern = '|'.join(escaped_chars)

                if (
                    char_class_pattern
                    and len(unique_chars) <= max_unique_chars_for_regex
                    and required_chars <= max_required_chars_for_regex
                ):
                    regex_pattern = f"([{char_class_pattern}].*?){{{required_chars},}}"
                    regex_query = {
                        "$or": [
                            {"en_core": {"$regex": regex_pattern, "$options": "i"}},
                            {"zh_core": {"$regex": regex_pattern, "$options": "i"}},
                            {"en_variants": {"$regex": regex_pattern, "$options": "i"}},
                            {"zh_variants": {"$regex": regex_pattern, "$options": "i"}}
                        ]
                    }
                else:
                    # 中文也走 n-gram 托底（避免直接构造超大正则失败）
                    ngram_queries = self._build_char_ngram_queries(clean_no_ws, n=3, max_word_length=100)
            except Exception as e:
                logger.warning(f"中文正则构建失败: {e}")
        else:
             # 英文 Layer 2 logic: N-gram
             ngram_queries = self._build_char_ngram_queries(cand_text_stripped, n=3, max_word_length=100)

        # 执行查询 (Layer 2)
        potential_entities = []
        for entity_type in entity_categories:
            collection_name = {
                "apt": "apt_organizations",
                "tool": "attack_tools",
                "vuln": "vulnerabilities"
            }.get(entity_type)
            
            if not collection_name:
                continue
            
            collection = mongo_dict_manager.db_service.get_collection(collection_name)
            if collection is None:
                continue
            
            matched_in_coll = []
            try:
                if regex_query: # 中文
                    matched_in_coll = list(collection.find(regex_query).limit(100))
                elif ngram_queries: # 英文 N-gram
                    matched_in_coll = self._safe_query_with_fallback(collection, ngram_queries, cand_text_stripped)
            except Exception as e:
                logger.warning(f"Layer 2 查询失败: {e}")
                continue
                
            for ent in matched_in_coll:
                potential_entities.append((ent, entity_type))
        
        # 评估 Layer 2 结果 (计算相似度)
        if not potential_entities:
            return None, 0.0, has_structured_id

        # 归一化相似度计算
        for entity, entity_type in potential_entities:
            # 编号兼容性检查
            if has_structured_id:
                entity_name = entity.get("en_core", "")
                if not self._check_id_compatible(cand_text_stripped, entity_name):
                    continue
            
            names_to_check = [entity.get("en_core", ""), entity.get("zh_core", "")]
            names_to_check.extend(entity.get("en_variants", []))
            names_to_check.extend(entity.get("zh_variants", []))
            
            current_best_sim = 0.0
            current_best_str = ""
            
            for name in names_to_check:
                if not name:
                    continue
                # 使用 Levenshtein.ratio (与 Layer 1 保持一致，同时也比较健壮)
                sim = Levenshtein.ratio(cand_text_stripped.lower(), name.strip().lower())
                
                if sim > current_best_sim:
                    current_best_sim = sim
                    current_best_str = name
            
            if current_best_sim > best_similarity:
                best_similarity = current_best_sim
                best_match = {
                    "entity": entity,
                    "entity_type": entity_type,
                    "matched_string": current_best_str
                }
                
        return best_match, best_similarity, has_structured_id

    def _build_token_regex_query(self, cand_text: str, max_token_length: int = 20) -> Tuple[Optional[Dict], List[str]]:
        """
        Layer 1 辅助：构建基于分词的正则查询
        
        Args:
            cand_text: 候选文本
            max_token_length: 单词最大长度，超过此长度的单词将被忽略
            
        Returns:
            (query_dict, valid_tokens)
        """
        valid_tokens = []
        
        # 1. 先按逗号/分号等分隔符拆分，获取完整的组织名短语
        # 例如: "APT1,combolt kitty" -> ["APT1", "combolt kitty"]
        phrase_separators = r'[,，;；/]'
        phrases = re.split(phrase_separators, cand_text)
        
        for phrase in phrases:
            # 清理括号等，但保留空格（保持多词组织名完整）
            phrase_cleaned = re.sub(r'[()（）\[\]【】{}「」:：]', ' ', phrase)
            phrase_cleaned = ' '.join(phrase_cleaned.split())  # 合并连续空格
            phrase_cleaned = phrase_cleaned.strip()
            
            if not phrase_cleaned:
                continue
                
            # 如果短语长度合理且不是纯干扰词，作为完整token添加
            if 2 <= len(phrase_cleaned) <= 50:
                # 检查是否为纯干扰词短语
                phrase_words = phrase_cleaned.split()
                non_stop_words = [w for w in phrase_words 
                                  if w.lower() not in self.IGNORE_WORDS 
                                  and w.lower() not in self.GENERIC_TERMS]
                if non_stop_words:
                    valid_tokens.append(phrase_cleaned)
        
        # 2. 额外：按空格分词，提取单独的有效词汇作为补充
        # 清理所有分隔符后分词
        all_cleaned = re.sub(r'[()（）\[\]【】{}「」,，:：;；/]', ' ', cand_text)
        single_tokens = all_cleaned.split()
        
        for t in single_tokens:
            t_clean = t.strip()
            # 过滤1: 空或太短
            if not t_clean or len(t_clean) < 2:
                continue
            # 过滤2: 干扰词 (忽略大小写)
            if t_clean.lower() in self.IGNORE_WORDS or t_clean.lower() in self.GENERIC_TERMS:
                continue
            # 过滤3: 过长单词
            if len(t_clean) > max_token_length:
                continue
            # 过滤4: 避免与已有短语重复
            if t_clean not in valid_tokens:
                valid_tokens.append(t_clean)
            
        if not valid_tokens:
            return None, []
            
        # 3. 构建正则 (OR 逻辑)
        # 只要包含任意一个有效 Token 即可 (后续通过打分筛选)
        
        escaped_tokens = [re.escape(t) for t in valid_tokens]
        pattern_str = '|'.join(escaped_tokens)
        
        query = {
            "$or": [
                {"en_core": {"$regex": pattern_str, "$options": "i"}},
                {"en_variants": {"$regex": pattern_str, "$options": "i"}},
                # 中文核心或变体通常不含英文分词，除非是混合，暂且都查
                {"zh_core": {"$regex": pattern_str, "$options": "i"}},
                {"zh_variants": {"$regex": pattern_str, "$options": "i"}}
            ]
        }
        
        return query, valid_tokens


    def _should_enter_semantic_match(self, candidate: str) -> bool:
        """
        判断是否允许进入语义匹配（准入检查）
        
        Args:
            candidate: 候选字符串
            
        Returns:
            True = 允许进入语义匹配
            False = 拒绝，不进入语义匹配
        """
        # 拦截1: 纯中文短词（避免误匹配如"摩诃草" → "丝绸幽灵"）
        if re.fullmatch(r'[\u4e00-\u9fff]+', candidate):
            if len(candidate) <= 6:
                logger.debug(f"语义匹配拦截纯中文短词: {candidate}")
                return False
        
        # 拦截2: 含结构化编号但无其他有效内容
        structured_id = self._extract_structured_id(candidate)
        if structured_id:
            # 移除编号后的残余
            for pattern in self.STRUCTURED_PATTERNS:
                candidate_residue = re.sub(pattern, '', candidate, flags=re.IGNORECASE)
            residue = re.sub(r'[（()）\[\]【】\s]', '', candidate_residue).strip()
            if not residue or residue.lower() in self.GENERIC_TERMS:
                logger.debug(f"语义匹配拦截纯编号: {candidate}")
                return False
        
        # 准入: 有后缀修饰词（BERT优势场景）
        SUFFIX_KEYWORDS = ["APT组织", "APT团伙", "组织", "团伙", "Group", "APT"]
        if any(kw in candidate for kw in SUFFIX_KEYWORDS):
            return True
        
        # 准入: 有括号（BERT优势场景）
        if re.search(r'[（(].*[）)]', candidate):
            return True
        
        # 准入: 短英文词（可能是简写，BERT优势场景）
        if len(candidate) <= 10 and re.match(r'^[a-zA-Z]+$', candidate):
            return True
        
        # 默认拒绝
        logger.debug(f"语义匹配准入失败: {candidate}")
    def semantic_match(
        self,
        candidates: List[Dict],  # 候选对象列表
        matched_candidates: Set[str],
        mongo_dict_manager: MongoDictManager,
        entity_categories: List[str],
        original_text: str = ""  # 保留但不使用
    ) -> Tuple[List[Dict], Set[str]]:
        """
        语义匹配（补充优先级，处理精确/模糊未命中的候选）
        
        实现步骤：
        1. 向量转换：将候选字符串转换为768维向量
        2. 实体向量缓存：提取实体的en_core+zh_core，转换为向量并缓存（首次加载时缓存，后续复用）
        3. 语义相似度计算：计算候选向量与实体向量的余弦相似度
        4. 结果筛选：仅保留相似度最高的实体，若相似度≥阈值则标记为semantic
        
        Args:
            candidates: 候选对象列表 [{"text": str, "start_pos": int, "end_pos": int}, ...]
            matched_candidates: 已匹配的候选字符串集合（避免重复匹配）
            mongo_dict_manager: 词典管理器实例
            entity_categories: 实体类别列表
        
        Returns:
            (匹配结果列表, 已匹配的候选字符串集合)
        """
        logger.debug(f"语义匹配开始，实体类别: {entity_categories}, 候选数量: {len(candidates)}, 已匹配: {len(matched_candidates)}")
        
        # 检查BERT模型是否已加载
        if not self._model_loaded or self.bert_model is None:
            logger.warning("BERT 模型未加载，跳过语义匹配")
            return [], matched_candidates.copy()
        
        results = []
        # 使用传入的已匹配候选集合，避免重复匹配
        current_matched_candidates = matched_candidates.copy()
        
        # 准入控制：筛选符合条件的候选对象
        remaining_candidate_objs = []
        for cand_obj in candidates:
            cand_text = cand_obj["text"]
            c_strip = cand_text.strip()
            if c_strip in current_matched_candidates:
                continue
            
            # 应用准入规则
            if not self._should_enter_semantic_match(c_strip):
                continue
                
            remaining_candidate_objs.append(cand_obj)

        
        if not remaining_candidate_objs:
            logger.debug("没有剩余候选字符串需要语义匹配")
            return results, current_matched_candidates
        
        # 提取候选文本用于BERT编码
        remaining_candidates = [obj["text"] for obj in remaining_candidate_objs]
        logger.debug(f"剩余候选字符串数量: {len(remaining_candidates)}")
        
        # ========== 步骤1：向量转换 - 将候选字符串转换为向量 ==========
        try:
            candidate_vectors = self.bert_model.encode(
                remaining_candidates,
                convert_to_numpy=True,
                normalize_embeddings=True,  # 归一化以便计算余弦相似度
                show_progress_bar=False
            )
            logger.debug(f"候选字符串向量化完成，向量维度: {candidate_vectors.shape}")
        except Exception as e:
            logger.error(f"候选字符串向量化失败: {str(e)}")
            return results, current_matched_candidates
        
        # ========== 步骤2：实体向量缓存 - 提取en_core+zh_core并转换为向量 ==========
        entity_vectors = {}  # {entity_id: vector}
        entity_info = {}  # {entity_id: entity_info}
        
        for entity_type in entity_categories:
            collection_name = {
                "apt": "apt_organizations",
                "tool": "attack_tools",
                "vuln": "vulnerabilities"
            }.get(entity_type)
            
            if not collection_name:
                continue
            
            collection = mongo_dict_manager.db_service.get_collection(collection_name)
            if collection is None:
                continue
            
            # 获取该类别下的所有实体
            entities = list(collection.find({}))
            logger.debug(f"从 {collection_name} 集合获取了 {len(entities)} 个实体")
            
            for entity in entities:
                entity_id = entity.get("entity_id")
                if not entity_id:
                    continue
                
                en_core = entity.get("en_core", "")
                zh_core = entity.get("zh_core", "")
                
                # 提取en_core+zh_core（组合核心名称）
                # 优先使用en_core，如果没有则使用zh_core，如果都有则组合
                core_text = ""
                if en_core and zh_core:
                    core_text = f"{en_core} {zh_core}".strip()
                elif en_core:
                    core_text = en_core
                elif zh_core:
                    core_text = zh_core
                
                if not core_text:
                    logger.warning(f"实体 {entity_id} 没有核心名称，跳过")
                    continue

                # 获取实体向量（优先从缓存读取，首次加载时缓存）
                try:
                    vector = self._get_entity_vector(entity_id, en_core, zh_core)
                    entity_vectors[entity_id] = vector
                    entity_info[entity_id] = {
                        "entity": entity,
                        "entity_type": entity_type,
                        "en_core": en_core,
                        "zh_core": zh_core,
                        "core_text": core_text
                    }
                except Exception as e:
                    logger.warning(f"获取实体 {entity_id} 的向量失败: {str(e)}")
                    continue
        
        if not entity_vectors:
            logger.warning("没有可用的实体向量，跳过语义匹配")
            return results, current_matched_candidates
        
        logger.debug(f"共获取 {len(entity_vectors)} 个实体向量")
        
        # ========== 步骤3：语义相似度计算 - 计算余弦相似度 ==========
        # ========== 步骤4：结果筛选 - 仅保留相似度最高的实体 ==========
        for idx, candidate in enumerate(remaining_candidates):
            candidate_vec = candidate_vectors[idx]
            best_match = None
            best_similarity = 0.0
            best_entity_id = None
            
            # 计算与所有实体的余弦相似度，找出相似度最高的
            for entity_id, entity_vec in entity_vectors.items():
                # 计算余弦相似度（向量已归一化，直接计算点积）
                similarity = self._calculate_cosine_similarity(candidate_vec, entity_vec)
                
                # 更新最佳匹配
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_entity_id = entity_id
            
            # 如果找到满足阈值的匹配（仅保留相似度最高的实体）
            if best_entity_id and best_similarity >= self.semantic_threshold:
                info = entity_info[best_entity_id]
                # 直接使用候选对象的位置信息
                candidate_obj = remaining_candidate_objs[idx]
                
                result = {
                    "entity_id": best_entity_id,
                    "entity_type": info["entity_type"],
                    "en_core": info["en_core"],
                    "zh_core": info["zh_core"],
                    "match_type": "semantic",
                    "confidence": round(best_similarity, 4),  # 置信度 = 余弦相似度
                    "matched_text": candidate,
                    "matched_field": "semantic",
                    "start_pos": candidate_obj["start_pos"],
                    "end_pos": candidate_obj["end_pos"]
                }
                results.append(result)
                current_matched_candidates.add(candidate)
                logger.debug(f"语义匹配成功: '{candidate}' -> {best_entity_id} (相似度: {best_similarity:.4f})")
            else:
                logger.debug(f"语义匹配未满足阈值: '{candidate}' (最高相似度: {best_similarity:.4f}, 阈值: {self.semantic_threshold})")
        
        # 后处理：过滤结构化数字差异导致的误报
        original_count = len(results)
        results = self._filter_structural_mismatches(results)
        filtered_count = original_count - len(results)
        
        logger.info(f"语义匹配找到 {len(results)} 个结果（阈值: {self.semantic_threshold}），后处理过滤了 {filtered_count} 条")
        return results, current_matched_candidates
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1（已归一化）
            vec2: 向量2（已归一化）
        
        Returns:
            余弦相似度值（0-1之间）
        """
        # 转换为 numpy 数组
        vec1 = np.array(vec1, dtype=np.float32)
        vec2 = np.array(vec2, dtype=np.float32)
        
        # 对于已归一化的向量，余弦相似度就是点积
        # Sentence-BERT 生成的向量已经归一化，所以直接计算点积即可
        cosine_sim = np.dot(vec1, vec2)
        
        # 确保结果在 0-1 范围内（理论上应该在 0-1 之间，但为了安全起见）
        cosine_sim = max(0.0, min(1.0, float(cosine_sim)))
        
        return cosine_sim
    
    def _has_structural_number_diff(self, text1: str, text2: str) -> bool:
        """
        检测两个字符串是否存在结构化命名中的数字差异
        
        用于过滤误报：如 APT-C-01 vs APT-C-06, TAG-38 vs TAG-53, UNC2596 vs UNC2589
        
        Args:
            text1: 原始文本（候选文本）
            text2: 匹配到的字段名
            
        Returns:
            True 如果检测到结构化数字差异（应该过滤），False 否则
        """
        import re
        from difflib import SequenceMatcher
        
        # 定义结构化命名模式（带数字的常见组织/工具/漏洞命名格式）
        STRUCTURED_PATTERNS = [
            # APT 组织编号（各种格式）
            r'APT-?[A-Z]-?\d+',       # APT-C-01, APT-Q-20, APT-A-xx (Generic)
            r'APT-?\d+',              # APT-1, APT1, APT-28, APT28
            r'TA\d+',                 # TA444, TA453
            r'TAG-?\d+',              # TAG-38, TAG-53
            r'UNC\d+',                # UNC2596, UNC2589
            r'UAC-?\d+',              # UAC-0020 (乌克兰CERT命名)
            
            # MITRE ATT&CK 编号
            r'[TGSC]-?\d+',           # T-1055, G-0016, S-0154, C-0001
            
            # 漏洞编号
            r'CVE-\d{4}-\d+',        # CVE-2021-44228, CVE-2021-45232
            r'MS\d{2}-\d+',          # MS17-010
            
            # 工具/恶意软件编号
            r'FIN\d+(?:\.\d+)?',     # FIN7, FIN7.5
            
            # 行动代号
            r'Operation\s+\w+',       # Operation GhostShell, Operation Troy
            
            # 厂商威胁命名
            r'Temp\.\w+',             # Temp.Periscope (FireEye)
            r'Sector[A-Z]\d+',        # SectorE02, SectorA01
            
            # 单位编号
            r'Unit\s+\d+',            # Unit 42, Unit 121
            
            # Group 相关（只匹配明确带数字的）
            r'\w+\s+Group\s*\d+',     # XXX Group 5
        ]
        
        # 检查是否匹配结构化模式
        def extract_numbers(text: str) -> set:
            """提取文本中的所有数字"""
            return set(re.findall(r'\d+', text))
        
        def matches_pattern(text: str) -> bool:
            """检查是否匹配任一结构化模式"""
            for pattern in STRUCTURED_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            return False
        
        # 如果两个文本都匹配结构化模式
        if matches_pattern(text1) and matches_pattern(text2):
            # 提取数字部分
            nums1 = extract_numbers(text1)
            nums2 = extract_numbers(text2)
            
            # 如果都含有数字且数字不完全相同，判定为结构化数字差异
            if nums1 and nums2 and nums1 != nums2:
                # 额外检查：去掉数字后的部分是否相似（避免误杀）
                text1_no_num = re.sub(r'\d+', '', text1).strip()
                text2_no_num = re.sub(r'\d+', '', text2).strip()
                
                # 如果去掉数字后的部分相似度高（比如都是 "APT-C-"），则认为是结构化差异
                if text1_no_num.lower() == text2_no_num.lower():
                    return True
                    
                # 对于 Operation/Unit 等开头的，检查前缀
                for prefix in ['operation', 'unit', 'tag', 'unc', 'apt', 'fin']:
                    if text1_no_num.lower().startswith(prefix) and text2_no_num.lower().startswith(prefix):
                        return True
        
        return False
    
    def _filter_structural_mismatches(self, results: List[Dict]) -> List[Dict]:
        """
        后处理：过滤掉因结构化数字差异导致的误报
        
        Args:
            results: 匹配结果列表
            
        Returns:
            过滤后的结果列表
        """
        filtered_results = []
        
        for result in results:
            matched_text = result.get("matched_text", "")
            matched_field = result.get("matched_field", "")
            
            # 检查是否是结构化数字差异
            if self._has_structural_number_diff(matched_text, matched_field):
                logger.debug(f"后处理过滤：数字差异误报 - '{matched_text}' vs '{matched_field}'")
                continue
                
            filtered_results.append(result)
        
        return filtered_results

    def _get_entity_vector(self, entity_id: str, en_core: str, zh_core: str) -> np.ndarray:
        """
        获取实体向量（优先从缓存读取，首次加载时缓存，后续复用）
        
        提取实体的en_core+zh_core（组合核心名称），转换为向量并缓存
        
        Args:
            entity_id: 实体ID
            en_core: 英文核心名称
            zh_core: 中文核心名称
        
        Returns:
            实体向量（768维，已归一化）
        """
        if not self._model_loaded or self.bert_model is None:
            raise ValueError("BERT 模型未加载，无法生成向量")
        
        # 1. 检查缓存（优先从缓存读取，提高性能）
        cached_vector = cache_service.get_vector_cache(entity_id)
        if cached_vector is not None:
            logger.debug(f"从缓存读取实体 {entity_id} 的向量")
            return np.array(cached_vector, dtype=np.float32)
        
        # 2. 如果缓存不存在，使用 BERT 模型生成向量
        # 提取en_core+zh_core（组合核心名称）
        # 优先组合：如果都有则组合，如果只有其中一个则使用该值
        core_text = ""
        if en_core and zh_core:
            core_text = f"{en_core} {zh_core}".strip()
        elif en_core:
            core_text = en_core
        elif zh_core:
            core_text = zh_core
        
        if not core_text:
            # 如果都没有，返回零向量
            logger.warning(f"实体 {entity_id} 没有核心名称，返回零向量")
            # 获取模型维度（如果模型已加载）
            if self.bert_model is not None:
                dim = self.bert_model.get_sentence_embedding_dimension()
                return np.zeros(dim, dtype=np.float32)
            else:
                return np.zeros(768, dtype=np.float32)  # 默认768维（all-MiniLM-L6-v2）
        
        # 3. 使用BERT模型生成向量（归一化以便计算余弦相似度）
        vector = self.bert_model.encode(
            core_text,
            convert_to_numpy=True,
            normalize_embeddings=True  # 归一化向量，便于计算余弦相似度
        )
        
        # 4. 将向量存入缓存（首次加载时缓存，后续复用）
        cache_service.set_vector_cache(entity_id, vector.tolist())
        logger.debug(f"实体 {entity_id} 的向量已生成并缓存（核心文本: {core_text}）")
        
        return vector
    
    def set_threshold(
        self,
        levenshtein_thresh: Optional[float] = None,
        semantic_thresh: Optional[float] = None
    ) -> bool:
        """
        动态调整匹配阈值
        
        Args:
            levenshtein_thresh: 模糊匹配阈值
            semantic_thresh: 语义匹配阈值
        
        Returns:
            是否设置成功
        """
        try:
            # 1. 校验阈值范围（0-1之间）
            if levenshtein_thresh is not None:
                if not 0 <= levenshtein_thresh <= 1:
                    logger.error(f"模糊匹配阈值超出范围: {levenshtein_thresh}")
                    return False
                self.levenshtein_threshold = levenshtein_thresh
                logger.info(f"模糊匹配阈值已更新为: {levenshtein_thresh}")
            
            if semantic_thresh is not None:
                if not 0 <= semantic_thresh <= 1:
                    logger.error(f"语义匹配阈值超出范围: {semantic_thresh}")
                    return False
                self.semantic_threshold = semantic_thresh
                logger.info(f"语义匹配阈值已更新为: {semantic_thresh}")
            
            return True
            
        except Exception as e:
            logger.error(f"设置阈值失败: {str(e)}")
            return False
    
    def _preprocess_text(
        self,
        text: str,
        mongo_dict_manager: MongoDictManager,
        entity_categories: List[str]
    ) -> Tuple[str, List[Dict]]:
        """
        文本预处理（支持 JSON 和 TXT 格式）
        
        Args:
            text: 输入文本（JSON 或 TXT 格式）
            mongo_dict_manager: 词典管理器实例
            entity_categories: 实体类别列表
        
        Returns:
            (原文, 候选对象列表)
        """
        logger.info(
            f"[CALL] _preprocess_text(text_len={len(text) if text else 0}, "
            f"entity_categories={entity_categories})"
        )
        # 兼容直接调用 _preprocess_text 的场景（例如路由前置预处理）
        # 避免 _find_text_position 访问未初始化的 used_positions
        if not hasattr(self, "used_positions") or self.used_positions is None:
            self.used_positions = set()
        import json

        stripped_text = text.strip()
        
        # 尝试解析为 JSON
        try:
            json_data = json.loads(stripped_text)
            logger.info("识别为 JSON 格式，提取候选字符串")
            
            # 提取原文
            if isinstance(json_data, dict) and "text" in json_data:
                original_text = json_data["text"]
            else:
                original_text = text
                
            logger.info(f"提取原文长度: {len(original_text)}")
            candidates = self._extract_candidates_from_json(json_data)
            
            # 按长度降序排序
            candidates.sort(key=lambda x: len(x), reverse=True)
            
            # 为每个候选计算位置
            candidate_objects = []
            for cand_text in candidates:
                start_pos, end_pos = self._find_text_position(original_text, cand_text)
                candidate_objects.append({
                    "text": cand_text,
                    "start_pos": start_pos,
                    "end_pos": end_pos
                })
            
            logger.debug(f"从JSON提取了 {len(candidate_objects)} 个候选字符串")
            return original_text, candidate_objects

        except json.JSONDecodeError:
            # 不是 JSON 格式：按 demo 的分句/分词/n-gram 候选逻辑生成
            logger.info("识别为非 JSON 文本，使用 TokenizerPipeline 生成候选")
            original_text = stripped_text

            if not original_text:
                return original_text, []

            def _simple_find_pos(haystack: str, needle: str) -> Tuple[int, int]:
                """不依赖 used_positions 的简单位置查找（避免候选重叠导致大量 -1）"""
                if not haystack or not needle:
                    return (-1, -1)
                pos = haystack.lower().find(needle.lower())
                if pos == -1:
                    return (-1, -1)
                return (pos, pos + len(needle))

            try:
                tokenize_result = self.tokenizer_pipeline.process(original_text)
                all_candidates = tokenize_result.get("all_candidates", [])
            except Exception as e:
                logger.warning(f"TokenizerPipeline 处理失败，回退到简单分句：{e}")
                sentences = self._segment_sentences_for_txt(original_text)
                candidate_objects = []
                for sentence in sentences:
                    sentence_stripped = sentence.strip()
                    if not sentence_stripped:
                        continue
                    start_pos, end_pos = self._find_text_position(original_text, sentence_stripped)
                    candidate_objects.append({
                        "text": sentence_stripped,
                        "start_pos": start_pos,
                        "end_pos": end_pos
                    })
                logger.info(f"回退后获得 {len(candidate_objects)} 个句子候选")
                return original_text, candidate_objects

            if not all_candidates:
                logger.warning("TokenizerPipeline 未生成候选")
                return original_text, []

            # 降低候选规模（避免 exact/fuzzy 阶段 DB 查询过多）
            max_candidates = 3000
            all_candidates.sort(
                key=lambda c: (
                    -float(c.get("confidence", 0.0)),
                    -int(c.get("ngram_size", 0)),
                    -len(str(c.get("text", "")))
                )
            )
            all_candidates = all_candidates[:max_candidates]

            candidate_objects: List[Dict] = []
            for cand in all_candidates:
                cand_text = str(cand.get("text", "")).strip()
                if not cand_text or len(cand_text) < 2:
                    continue

                # 中文候选如果带空格（n-gram 拼接可能插入空格），优先尝试去空格再用于匹配
                if any('\u4e00' <= ch <= '\u9fff' for ch in cand_text) and re.search(r'\s+', cand_text):
                    cand_no_ws = re.sub(r'\s+', '', cand_text)
                    if cand_no_ws and len(cand_no_ws) >= 2:
                        start_pos, end_pos = _simple_find_pos(original_text, cand_no_ws)
                        if start_pos != -1:
                            cand_text = cand_no_ws

                # 拦截通用干扰词，减少无效 DB 查询
                if self._is_generic_term(cand_text):
                    continue

                start_pos, end_pos = _simple_find_pos(original_text, cand_text)
                candidate_objects.append({
                    "text": cand_text,
                    "start_pos": start_pos,
                    "end_pos": end_pos
                })

            logger.info(
                f"TokenizerPipeline 候选生成：原始候选 {len(all_candidates)}，"
                f"过滤后 {len(candidate_objects)}"
            )
            return original_text, candidate_objects
            
        except Exception as e:
            error_msg = f"文本处理异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return "", []
    
    def _segment_sentences_for_txt(self, text: str) -> List[str]:
        """
        对 TXT 文本进行分句处理
        
        Args:
            text: 输入的原始文本
        
        Returns:
            句子列表
        """
        import re
        
        if not text.strip():
            return []
        
        # 分句规则：使用中文和英文的句子终止符
        # 中文：。！？ 
        # 英文：. ! ? 但需要避免缩写等情况
        
        # 首先按照中文句号、感叹号、问号分割
        # 然后按照英文句号、感叹号、问号分割（但通过简化处理）
        
        sentences = []
        current_sentence = ""
        
        for i, char in enumerate(text):
            current_sentence += char
            
            # 检查是否是句子终止符
            is_terminator = char in '。！？'
            
            # 对于英文句号，简单处理（避免处理缩写等复杂情况）
            if char == '.' or char == '!' or char == '?':
                # 检查是否是真正的句子终止（简单启发式）
                is_terminator = True
                # 如果后面还有空格或者是文本末尾，则认为是真正的终止
                if i + 1 < len(text):
                    next_char = text[i + 1]
                    # 如果下一个字符不是空格或大写字母，可能不是句子终止
                    if next_char not in ' \n\r' and not next_char.isupper() and next_char not in '。！？':
                        is_terminator = False
            
            if is_terminator:
                sentence = current_sentence.strip()
                if sentence and len(sentence) > 1:  # 只保留非空且长度>1的句子
                    sentences.append(sentence)
                current_sentence = ""
        
        # 处理最后未被终止的文本
        if current_sentence.strip():
            sentence = current_sentence.strip()
            if len(sentence) > 1:
                sentences.append(sentence)
        
        logger.debug(f"TXT 分句完成，共 {len(sentences)} 个句子")
        
        # 去除过短的句子（可选，避免噪音）
        # 这里保留所有句子，由后续的匹配逻辑来处理
        
        return sentences


    def _extract_candidates_from_json(self, json_data) -> List[str]:
        """
        从JSON数据中提取候选字符串

        Args:
            json_data: JSON数据（可以是字典或列表）

        Returns:
            候选字符串列表
        """
        candidates = []

        try:
            if isinstance(json_data, list):
                # 如果是列表，直接视为候选列表
                candidates.extend(json_data)
            elif isinstance(json_data, dict):
                # 优先处理包装格式：{"candidates": [...]}
                if "candidates" in json_data and isinstance(json_data["candidates"], list):
                    candidates = json_data["candidates"]
                else:
                    # 兼容原始格式：直接包含group_set, tool_set, vul_set
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

        # 打印JSON候选字符串列表
        print(f"JSON候选字符串 ({len(candidates)} 个): {candidates}")
        return candidates
        