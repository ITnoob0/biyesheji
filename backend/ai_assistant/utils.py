# backend/ai_assistant/utils.py
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
import json

class AcademicAI:
    def __init__(self, model_name="qwen2.5:3b"):
        # 针对 RTX 3050 Ti 优化，使用轻量级 3B 模型
        self.llm = Ollama(model=model_name)

    def extract_tags(self, title, abstract):
        """分析标题和摘要，提取核心关键词"""
        template = """
        作为一名科研管理专家，请分析以下论文。
        要求：提取 5 个核心研究关键词。
        注意：仅返回一个 JSON 数组，例如 ["关键词1", "关键词2"]，严禁输出任何多余解释。
        
        论文标题：{title}
        论文摘要：{abstract}
        """
        prompt = PromptTemplate.from_template(template)
        try:
            response = self.llm.invoke(prompt.format(title=title, abstract=abstract))
            # 自动清洗可能存在的 Markdown 标签
            clean_res = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_res)
        except Exception as e:
            print(f"AI 提取失败: {e}")
            return ["待分类"]