# backend/ai_assistant/utils.py
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
import json

class AcademicAI:
    # 1. 将默认模型名改为与你启动命令一致的 qwen2.5-fast
    def __init__(self, model_name="qwen2.5-fast"):
        # 2. 增加 temperature=0，让模型输出更像“机器”一样严谨，减少幻觉
        self.llm = Ollama(model=model_name, temperature=0)

    def extract_tags(self, title, abstract):
        # 3. 优化提示词：明确兜底动作，禁止自创诸如“待分类”的词汇
        template = """
        请作为学术助手，为下述论文提取5个核心研究关键词。
        要求：
        1. 仅返回一个 JSON 数组格式，例如 ["标签1", "标签2", "标签3", "标签4", "标签5"]。
        2. 严禁返回任何多余的解释、前言或 Markdown 标签。
        3. 如果提供的内容无意义或无法提取出学术关键词，请固定返回 ["无法提取"]，绝对不要自行生造如"待分类"等词汇。
        
        标题：{title}
        摘要：{abstract}
        """
        prompt = PromptTemplate.from_template(template)
        try:
            response = self.llm.invoke(prompt.format(title=title, abstract=abstract))
            
            clean_res = response.strip()
            if "```" in clean_res:
                clean_res = clean_res.split("```")[1]
                if clean_res.startswith("json"):
                    clean_res = clean_res[4:]
            
            return json.loads(clean_res.strip())
        except Exception as e:
            print(f"AI 提取失败，详细错误信息: {e}") 
            return ["分析异常"]