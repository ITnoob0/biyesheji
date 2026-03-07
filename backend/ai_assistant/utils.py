# backend/ai_assistant/utils.py
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
import json

class AcademicAI:
    def __init__(self, model_name="qwen2.5:3b"):
        # 针对 RTX 3050 Ti 优化，使用轻量级 3B 模型
        self.llm = Ollama(model=model_name)

    def extract_tags(self, title, abstract):
        # 优化提示词，明确告诉它只需要输出一个干净的列表
        template = """
        请作为学术助手，为下述论文提取5个核心关键词。
        要求：
        1. 仅返回一个 JSON 数组格式，例如 ["标签1", "标签2", "标签3", "标签4", "标签5"]。
        2. 严禁返回任何多余的解释、前言或 Markdown 标签。
        
        标题：{title}
        摘要：{abstract}
        """
        prompt = PromptTemplate.from_template(template)
        try:
            response = self.llm.invoke(prompt.format(title=title, abstract=abstract))
            # 增强清洗逻辑：去除可能存在的所有 Markdown 格式代码块
            clean_res = response.strip()
            if "```" in clean_res:
                clean_res = clean_res.split("```")[1]
                if clean_res.startswith("json"):
                    clean_res = clean_res[4:]
            
            return json.loads(clean_res.strip())
        except Exception as e:
            # 这里的 print 会显示在你的终端，请查看它
            print(f"AI 提取失败，详细错误信息: {e}") 
            return ["分析异常"]