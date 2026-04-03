"""
核心分词模块 - 支持中英混合分词、短语保护、词性标注、n-gram生成和通用词衰减

来源: app/demo/tokenizer_demo.py
说明: 这是从demo中提取的生产级模块，包含所有分词处理逻辑
"""

import re
from typing import List, Dict, Tuple, Optional


# ==================== 第一部分：分句模块 ====================

class SentenceSegmenter:
    """中英混合文本分句器"""
    
    # 英文常见缩写词表
    ENGLISH_ABBREVIATIONS = {
        'mr', 'mrs', 'dr', 'ms', 'prof', 'rev', 'hon',
        'i.e', 'e.g', 'etc', 'vs', 'vs.',
        'u.s', 'u.k', 'b.c', 'a.d',
    }
    
    def __init__(self):
        self.min_sentence_length = 2
    
    def segment(self, text: str) -> List[Dict]:
        """分句处理"""
        if not text or not text.strip():
            return []
        
        sentences = []
        current_sentence = ""
        start_pos = 0
        sentence_id = 0
        
        for i, char in enumerate(text):
            current_sentence += char
            is_sentence_end = False
            
            if char in '。！？\n':
                is_sentence_end = True
            elif char in '.!?':
                if char == '.':
                    words_before_dot = current_sentence[:-1].split()
                    if words_before_dot:
                        last_word = words_before_dot[-1].lower().rstrip(',;:')
                        if last_word in self.ENGLISH_ABBREVIATIONS:
                            is_sentence_end = False
                        else:
                            if i + 1 < len(text):
                                next_char = text[i + 1]
                                if next_char in ' \t\n' and i + 2 < len(text) and text[i + 2].isupper():
                                    is_sentence_end = True
                            else:
                                is_sentence_end = True
                else:
                    is_sentence_end = True
            
            if is_sentence_end:
                sentence_text = current_sentence.strip()
                if len(sentence_text) > self.min_sentence_length:
                    sentences.append({
                        "id": sentence_id,
                        "text": sentence_text,
                        "start_pos": start_pos,
                        "end_pos": i + 1,
                        "length": len(sentence_text)
                    })
                    sentence_id += 1
                
                current_sentence = ""
                start_pos = i + 1
        
        # 处理末尾未被终止的文本
        if current_sentence.strip():
            sentence_text = current_sentence.strip()
            if len(sentence_text) > self.min_sentence_length:
                sentences.append({
                    "id": sentence_id,
                    "text": sentence_text,
                    "start_pos": start_pos,
                    "end_pos": len(text),
                    "length": len(sentence_text)
                })
        
        return sentences


# ==================== 第二部分：词性标注模块 ====================

class POSTagging:
    """词性标注（使用nltk和jieba）"""
    
    EN_POS_WEIGHTS = {
        "NNP": 0.95, "NNPS": 0.95, "NN": 0.5, "NNS": 0.5,
        "VB": 0.1, "JJ": 0.1, "IN": 0.05, "DT": 0.05,
        "CD": 0.6, "FW": 0.8,
    }
    
    ZH_POS_WEIGHTS = {
        "nt": 0.9, "nr": 0.85, "ns": 0.85, "n": 0.6, "nz": 0.7,
        "v": 0.1, "a": 0.1, "m": 0.5,
    }
    
    @classmethod
    def try_nltk_pos_tag(cls, tokens: List[str]) -> Optional[List[Tuple[str, str]]]:
        """尝试使用nltk进行词性标注"""
        try:
            import nltk
            from nltk import pos_tag
            try:
                nltk.data.find('taggers/averaged_perceptron_tagger')
            except LookupError:
                nltk.download('averaged_perceptron_tagger', quiet=True)
            return pos_tag(tokens)
        except:
            return None
    
    @classmethod
    def try_jieba_pos_tag(cls, text: str) -> Optional[List[Tuple[str, str]]]:
        """尝试使用jieba进行词性标注"""
        try:
            import jieba.posseg as pseg
            return [(w, p) for w, p in pseg.cut(text)]
        except:
            return None
    
    @classmethod
    def get_pos_weight(cls, word: str, pos_tag: str, language: str) -> float:
        """获取词性权重"""
        if language == "en":
            return cls.EN_POS_WEIGHTS.get(pos_tag, 0.3)
        elif language == "zh":
            return cls.ZH_POS_WEIGHTS.get(pos_tag, 0.3)
        else:
            return 0.3


# ==================== 第三部分：短语保护模块 ====================

class PhraseProtector:
    """多词短语保护"""
    
    def __init__(self, phrases: Optional[Dict[str, List[str]]] = None):
        if phrases is None:
            phrases = {"en": [], "zh": []}
        self.en_phrases = sorted(phrases.get("en", []), key=len, reverse=True)
        self.zh_phrases = sorted(phrases.get("zh", []), key=len, reverse=True)
        self.phrase_mapping = {}
    
    def protect(self, text: str) -> Tuple[str, Dict]:
        """用占位符保护短语"""
        protected_text = text
        self.phrase_mapping = {}
        counter = 0
        
        for phrase in self.en_phrases:
            placeholder = f"__EN_PHRASE_{counter}__"
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            protected_text = pattern.sub(placeholder, protected_text)
            self.phrase_mapping[placeholder] = phrase
            counter += 1
        
        for phrase in self.zh_phrases:
            placeholder = f"__ZH_PHRASE_{counter}__"
            protected_text = protected_text.replace(phrase, placeholder)
            self.phrase_mapping[placeholder] = phrase
            counter += 1
        
        return protected_text, self.phrase_mapping
    
    def restore(self, tokens: List[str]) -> List[str]:
        """恢复被保护的短语"""
        restored = []
        for token in tokens:
            if token in self.phrase_mapping:
                restored.append(self.phrase_mapping[token])
            else:
                restored.append(token)
        return restored


# ==================== 第四部分：分词模块 ====================

class Tokenizer:
    """中英混合文本分词器"""
    
    def __init__(self, phrases: Optional[Dict[str, List[str]]] = None):
        self.protector = PhraseProtector(phrases)
        self.pos_tagging = POSTagging()
    
    def tokenize_english(self, text: str) -> List[str]:
        """英文分词"""
        pattern = r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*|__[A-Z_0-9]+__'
        tokens = re.findall(pattern, text)
        return tokens
    
    def tokenize_chinese(self, text: str) -> List[str]:
        """中文分词"""
        try:
            import jieba
            tokens = list(jieba.cut(text, cut_all=False))
            tokens = [t for t in tokens if t.strip() and len(t) >= 1]
            return tokens
        except ImportError:
            return [c for c in text if '\u4e00' <= c <= '\u9fff']
    
    def detect_language(self, text: str) -> str:
        """检测文本主要语言"""
        zh_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_count = sum(1 for c in text if c.isalpha())
        
        total = zh_count + en_count
        if total == 0:
            return "unknown"
        
        zh_ratio = zh_count / total
        if zh_ratio > 0.6:
            return "zh"
        elif zh_ratio < 0.4:
            return "en"
        else:
            return "mixed"
    
    def tokenize(self, text: str) -> Dict:
        """完整分词流程"""
        protected_text, phrase_map = self.protector.protect(text)
        language = self.detect_language(protected_text)
        
        if language == "zh":
            tokens = self.tokenize_chinese(protected_text)
        elif language == "en":
            tokens = self.tokenize_english(protected_text)
        else:
            tokens = self._tokenize_mixed(protected_text)
        
        tokens = self.protector.restore(tokens)
        tokens_with_pos = self._add_pos_tags(tokens, language)
        
        return {
            "text": text,
            "language": language,
            "tokens": tokens,
            "tokens_with_pos": tokens_with_pos,
            "phrase_map": phrase_map
        }
    
    def _tokenize_mixed(self, text: str) -> List[str]:
        """针对混合文本的分词"""
        tokens = []
        current_word = ""
        current_lang = None
        
        for char in text:
            is_zh = '\u4e00' <= char <= '\u9fff'
            is_en = char.isalpha() or char.isdigit()
            
            if is_zh:
                if current_lang == "en" and current_word:
                    tokens.append(current_word)
                    current_word = ""
                
                if current_lang != "zh":
                    current_lang = "zh"
                    current_word = char
                else:
                    current_word += char
            
            elif is_en:
                if current_lang == "zh" and current_word:
                    zh_tokens = self.tokenize_chinese(current_word)
                    tokens.extend(zh_tokens)
                    current_word = ""
                
                if current_lang != "en":
                    current_lang = "en"
                
                current_word += char
            
            else:
                if current_lang == "zh" and current_word:
                    zh_tokens = self.tokenize_chinese(current_word)
                    tokens.extend(zh_tokens)
                    current_word = ""
                elif current_lang == "en" and current_word:
                    tokens.append(current_word)
                    current_word = ""
                
                current_lang = None
        
        if current_lang == "zh" and current_word:
            zh_tokens = self.tokenize_chinese(current_word)
            tokens.extend(zh_tokens)
        elif current_lang == "en" and current_word:
            tokens.append(current_word)
        
        return [t for t in tokens if t.strip()]
    
    def _add_pos_tags(self, tokens: List[str], language: str) -> List[Dict]:
        """为tokens添加词性标注"""
        tokens_with_pos = []
        
        if language == "en":
            pos_results = self.pos_tagging.try_nltk_pos_tag(tokens)
            if pos_results:
                for token, pos in pos_results:
                    weight = self.pos_tagging.get_pos_weight(token, pos, "en")
                    tokens_with_pos.append({
                        "text": token,
                        "pos": pos,
                        "pos_weight": weight
                    })
            else:
                for token in tokens:
                    is_proper = token[0].isupper() if token else False
                    pos = "NNP" if is_proper else "NN"
                    weight = 0.95 if is_proper else 0.5
                    tokens_with_pos.append({
                        "text": token,
                        "pos": pos,
                        "pos_weight": weight
                    })
        
        elif language == "zh":
            text_for_tagging = " ".join(tokens)
            pos_results = self.pos_tagging.try_jieba_pos_tag(text_for_tagging)
            if pos_results:
                for token, pos in pos_results:
                    if token.strip():
                        weight = self.pos_tagging.get_pos_weight(token, pos, "zh")
                        tokens_with_pos.append({
                            "text": token,
                            "pos": pos,
                            "pos_weight": weight
                        })
            else:
                for token in tokens:
                    if not token.strip():
                        continue
                    
                    if len(token) >= 2:
                        pos = "nt"
                        weight = 0.7 if len(token) >= 3 else 0.6
                    else:
                        pos = "n"
                        weight = 0.3
                    
                    tokens_with_pos.append({
                        "text": token,
                        "pos": pos,
                        "pos_weight": weight
                    })
        
        else:
            for token in tokens:
                is_zh = any('\u4e00' <= c <= '\u9fff' for c in token)
                if is_zh:
                    pos = "nt" if len(token) >= 2 else "n"
                    pos_weight = 0.8 if len(token) >= 2 else 0.4
                else:
                    is_proper = token[0].isupper() if token else False
                    pos = "NNP" if is_proper else "NN"
                    pos_weight = 0.95 if is_proper else 0.5
                
                tokens_with_pos.append({
                    "text": token,
                    "pos": pos,
                    "pos_weight": pos_weight
                })
        
        return tokens_with_pos


# ==================== 第五部分：n-gram候选生成 ====================

class NGramCandidateGenerator:
    """n-gram候选生成和评分（含通用词衰减）"""
    
    STRUCTURED_PATTERNS = [
        r'APT-?[A-Z]-?\d+', r'APT[-_]?\d+', r'CVE-\d{4}-\d+', r'[A-Z]{2,}\d+',
    ]
    
    # 通用词衰减权重表（分4层）
    GENERIC_WORDS_WEIGHTED = {
        # 第1层（权重0.3）：纯描述词
        "分析": 0.3, "报告": 0.3, "评估": 0.3, "防御": 0.3, "检查": 0.3,
        "说明": 0.3, "描述": 0.3, "总结": 0.3, "详细": 0.3, "深入": 0.3,
        "分类": 0.3, "审计": 0.3, "综述": 0.3,
        "analysis": 0.3, "report": 0.3, "assessment": 0.3, "detection": 0.3,
        "review": 0.3, "summary": 0.3, "description": 0.3,
        
        # 第2层（权重0.5）：通用分类词
        "组织": 0.5, "团队": 0.5, "小组": 0.5, "团伙": 0.5, "集团": 0.5,
        "公司": 0.5, "企业": 0.5, "机构": 0.5, "工具": 0.5, "系统": 0.5,
        "平台": 0.5, "框架": 0.5, "方案": 0.5, "事件": 0.5, "行为": 0.5,
        "威胁": 0.5, "风险": 0.5, "漏洞": 0.5, "缺陷": 0.5, "错误": 0.5,
        "攻击": 0.5, "防护": 0.5, "防守": 0.5, "活动": 0.5, "行为体": 0.5,
        "group": 0.5, "team": 0.5, "actor": 0.5, "organization": 0.5,
        "activity": 0.5, "threat": 0.5, "tool": 0.5, "system": 0.5,
        "platform": 0.5, "vulnerability": 0.5, "malware": 0.5,
        
        # 第3层（权重0.6）：操作/行为动词与连接词
        "执行": 0.6, "部署": 0.6, "进行": 0.6, "使用": 0.6, "利用": 0.6,
        "进入": 0.6, "采用": 0.6, "实施": 0.6, "开展": 0.6, "发起": 0.6,
        "发现": 0.6, "检测": 0.6, "确认": 0.6, "验证": 0.6, "识别": 0.6,
        "活跃": 0.6, "相关": 0.6, "包括": 0.6, "涉及": 0.6, "导致": 0.6,
        "造成": 0.6, "针对": 0.6, "影响": 0.6, "应用": 0.6, "支持": 0.6,
        "executed": 0.6, "deployed": 0.6, "performed": 0.6, "used": 0.6,
        "targeting": 0.6, "identified": 0.6, "confirmed": 0.6, "detected": 0.6,
        "included": 0.6, "conducted": 0.6, "involved": 0.6,
        
        # 第4层（权重0.7）：泛指修饰词
        "持续": 0.7, "重大": 0.7, "关键": 0.7, "常见": 0.7, "特定": 0.7,
        "多个": 0.7, "多种": 0.7, "多次": 0.7, "多地": 0.7, "大规模": 0.7,
        "高级": 0.7, "高度": 0.7, "跨地域": 0.7, "跨越": 0.7, "全球": 0.7,
        "广泛": 0.7, "普遍": 0.7, "中期": 0.7, "后期": 0.7, "初期": 0.7,
        "similar": 0.7, "related": 0.7,
        "significant": 0.7, "continuous": 0.7, "multiple": 0.7, "various": 0.7,
        "widespread": 0.7, "extensive": 0.7, "global": 0.7, "advanced": 0.7,
    }
    
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
    
    def generate(self, tokens_with_pos: List[Dict], max_ngram: int = 3) -> List[Dict]:
        """生成和评分n-gram候选"""
        candidates = []
        tokens = [t["text"] for t in tokens_with_pos]
        pos_tags = [t["pos"] for t in tokens_with_pos]
        pos_weights = [t["pos_weight"] for t in tokens_with_pos]
        
        for n in range(1, min(max_ngram + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram_tokens = tokens[i:i+n]
                ngram_text = " ".join(ngram_tokens) if n > 1 else ngram_tokens[0]
                ngram_pos = pos_tags[i:i+n]
                ngram_weights = pos_weights[i:i+n]
                
                confidence = self._compute_confidence(
                    ngram_tokens, ngram_text, ngram_pos, ngram_weights, n
                )
                
                if confidence >= self.min_confidence:
                    candidates.append({
                        "text": ngram_text,
                        "level": f"{n}gram",
                        "pos_sequence": ngram_pos,
                        "confidence": round(confidence, 3),
                        "has_structure_id": self._has_structure_id(ngram_text),
                        "ngram_size": n
                    })
        
        candidates.sort(key=lambda x: (-x["confidence"], -x["ngram_size"], -len(x["text"])))
        return candidates
    
    def _compute_confidence(
        self, tokens: List[str], text: str, pos_tags: List[str],
        pos_weights: List[float], ngram_size: int
    ) -> float:
        """计算候选的置信度（含通用词衰减）"""
        pos_score = sum(pos_weights) / len(pos_weights) if pos_weights else 0.3
        
        ngram_bonus = 0.15 if ngram_size >= 2 else 0.0
        structure_bonus = 0.2 if self._has_structure_id(text) else 0.0
        generic_weight = self._compute_generic_weight(tokens)
        
        base_score = min(pos_score + ngram_bonus + structure_bonus, 1.0)
        final_score = base_score * generic_weight
        return min(final_score, 1.0)
    
    def _compute_generic_weight(self, tokens: List[str]) -> float:
        """计算通用词衰减权重"""
        if not tokens:
            return 1.0
        
        weights = []
        for token in tokens:
            token_lower = token.lower()
            weight = self.GENERIC_WORDS_WEIGHTED.get(token_lower, 1.0)
            weights.append(weight)
        
        return min(weights) if weights else 1.0
    
    def _has_structure_id(self, text: str) -> bool:
        """检查文本是否含有结构化编号"""
        for pattern in self.STRUCTURED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


# ==================== 第六部分：核心Pipeline ====================

class TokenizerPipeline:
    """完整的分词pipeline"""
    
    def __init__(self, phrases: Optional[Dict[str, List[str]]] = None):
        self.segmenter = SentenceSegmenter()
        self.tokenizer = Tokenizer(phrases)
        self.ngram_generator = NGramCandidateGenerator(min_confidence=0.5)
    
    def process(self, text: str) -> Dict:
        """完整处理流程"""
        sentences = self.segmenter.segment(text)
        all_candidates = []
        
        for sentence in sentences:
            sentence_text = sentence["text"]
            tokenize_result = self.tokenizer.tokenize(sentence_text)
            
            ngram_candidates = self.ngram_generator.generate(
                tokenize_result["tokens_with_pos"],
                max_ngram=3
            )
            
            for candidate in ngram_candidates:
                candidate["sentence_id"] = sentence["id"]
                candidate["sentence_text"] = sentence_text
                candidate["language"] = tokenize_result["language"]
                all_candidates.append(candidate)
        
        return {
            "sentences": sentences,
            "all_candidates": all_candidates
        }
