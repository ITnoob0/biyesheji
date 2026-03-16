import json
import re
from collections import Counter

try:
    from langchain_community.llms import Ollama
    from langchain_core.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency fallback
    Ollama = None
    PromptTemplate = None


class AcademicAI:
    def __init__(self, model_name='qwen2.5-fast'):
        self.model_name = model_name
        self.llm = None

        if Ollama is not None:
            try:
                self.llm = Ollama(model=model_name, temperature=0)
            except Exception:
                self.llm = None

    def extract_tags(self, title, abstract):
        if not title and not abstract:
            return []

        if self.llm is None or PromptTemplate is None:
            return self._fallback_extract_tags(title, abstract)

        template = """
        请作为学术助手，为下述论文提取 3 到 5 个核心研究关键词。
        只返回 JSON 数组，例如 ["关键词1", "关键词2"]，不要返回其他解释。

        标题：{title}
        摘要：{abstract}
        """
        prompt = PromptTemplate.from_template(template)

        try:
            response = self.llm.invoke(prompt.format(title=title, abstract=abstract))
            parsed_tags = self._parse_llm_response(response)
            normalized_tags = self._normalize_tags(parsed_tags)
            if normalized_tags:
                return normalized_tags
        except Exception:
            pass

        return self._fallback_extract_tags(title, abstract)

    def _parse_llm_response(self, response):
        cleaned = str(response).strip()
        if '```' in cleaned:
            blocks = cleaned.split('```')
            cleaned = next((block for block in blocks if '[' in block and ']' in block), cleaned)
            if cleaned.startswith('json'):
                cleaned = cleaned[4:]

        parsed = json.loads(cleaned.strip())
        if isinstance(parsed, list):
            return parsed
        return []

    def _fallback_extract_tags(self, title, abstract):
        text = ' '.join(part for part in [title, abstract] if part)
        chinese_tokens = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        english_tokens = re.findall(r'[A-Za-z][A-Za-z\-]{2,}', text.lower())

        stopwords = {
            '研究', '方法', '分析', '设计', '系统', '模型', '数据', '高校', '教师', 'paper',
            'study', 'based', 'using', 'approach', 'analysis', 'method', 'results', 'system',
            'research', 'university', 'college', 'teacher',
        }

        tokens = [token.strip() for token in chinese_tokens + english_tokens]
        filtered_tokens = [token for token in tokens if token not in stopwords and len(token) >= 2]
        ranked_tokens = [token for token, _ in Counter(filtered_tokens).most_common(5)]
        return self._normalize_tags(ranked_tokens)

    def _normalize_tags(self, tags):
        normalized = []
        for tag in tags:
            clean_tag = str(tag).strip().strip('.,;:[]{}"\'')
            if not clean_tag:
                continue
            if clean_tag in {'无法提取', '分析异常'}:
                continue
            if clean_tag not in normalized:
                normalized.append(clean_tag)

        return normalized[:5]
