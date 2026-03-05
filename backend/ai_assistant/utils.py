# backend/ai_assistant/utils.py
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
import json

class AcademicAI:
    def __init__(self, model_name="qwen"): # 你可以根据本地安装的模型修改，如 llama3 或 gemma
        self.llm = Ollama(model=model_name)

    def extract_keywords(self, title, abstract):
        """
        输入论文标题和摘要，返回提取的关键词 JSON 列表
        """
        template = """
        你是一个专业的学术助手。请分析以下论文的标题和摘要，并提取出 5-8 个核心研究关键词。
        关键词应包含：研究领域、核心算法/技术、应用场景。
        
        论文标题：{title}
        论文摘要：{abstract}
        
        请仅返回一个标准的 JSON 格式列表，不要有任何多余的解释，格式如下：
        ["关键词1", "关键词2", "关键词3"]
        """
        prompt = PromptTemplate.from_template(template)
        try:
            response = self.llm.invoke(prompt.format(title=title, abstract=abstract))
            # 清洗可能存在的 markdown 标记
            clean_res = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_res)
        except Exception as e:
            print(f"AI 提取失败: {e}")
            return []