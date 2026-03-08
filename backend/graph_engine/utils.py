from neo4j import GraphDatabase

class Neo4jEngine:
    def __init__(self):
        # 请根据你本地 Neo4j 的实际情况修改密码
        self.uri = "bolt://localhost:7687"
        self.user = "neo4j"
        self.password = "liujianlei" # <-- 这里换成你的 Neo4j 密码
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def sync_paper_to_graph(self, paper_id, title, author_names, keywords):
        """
        将论文、作者、关键词及其关系写入图数据库
        """
        query = """
        // 1. 创建或找到论文节点 (MERGE 保证不会重复创建)
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title

        // 2. 遍历作者并建立 [发表] 关系
        WITH p
        UNWIND $author_names AS author_name
        MERGE (t:Teacher {name: author_name})
        MERGE (t)-[:PUBLISHED]->(p)

        // 3. 遍历关键词并建立 [包含] 关系，同时将关键词挂载给作者
        WITH p, t
        UNWIND $keywords AS kw
        MERGE (k:Keyword {name: kw})
        MERGE (p)-[:HAS_KEYWORD]->(k)
        MERGE (t)-[:RESEARCHES]->(k)
        """
        with self.driver.session() as session:
            session.run(query, 
                        paper_id=str(paper_id), 
                        title=title, 
                        author_names=author_names, 
                        keywords=keywords)
            print(f"✅ 成功将论文《{title}》及其关系网络同步至 Neo4j!")