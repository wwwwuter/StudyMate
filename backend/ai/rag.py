import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 知识库服务（Phase 0 预留接口，模型依赖 sentence_transformers/numpy 延迟加载）"""

    def __init__(self):
        self.embedding_model = None
        self.documents = []
        self.embeddings = None
        self._model_name = 'paraphrase-multilingual-MiniLM-L12-v2'

    def _load_embedding_model(self):
        """延迟加载 embedding 模型（仅在实际调用 RAG 时安装并加载）"""
        if self.embedding_model is None:
            try:
                # 延迟导入：sentence_transformers / numpy 属后续阶段 AI 依赖，
                # 避免在应用启动（create_app）时强制安装 torch 重依赖
                from sentence_transformers import SentenceTransformer
                import numpy as np
                self._np = np
                self.embedding_model = SentenceTransformer(self._model_name)
                logger.info(f'Embedding 模型加载成功: {self._model_name}')
            except Exception as e:
                logger.error(f'Embedding 模型加载失败: {e}')
                raise

    def add_document(self, text: str, chunk_size: int = 500):
        """添加文档并进行文本切片"""
        self._load_embedding_model()

        # 简单文本切片
        chunks = []
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        if not chunks:
            chunks = [text]

        self.documents.extend(chunks)

        # 生成向量
        new_embeddings = self.embedding_model.encode(chunks)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = self._np.vstack([self.embeddings, new_embeddings])

        logger.info(f'文档已添加，当前共 {len(self.documents)} 个文本块')
        return len(chunks)

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """检索相关文档"""
        if not self.documents:
            return []

        self._load_embedding_model()
        query_embedding = self.embedding_model.encode([query])

        # 计算余弦相似度
        scores = self._np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = self._np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if scores[idx] > 0.3:  # 相似度阈值
                results.append(self.documents[idx])

        return results

    def clear(self):
        """清空知识库"""
        self.documents = []
        self.embeddings = None
        logger.info('知识库已清空')

    # ------------------ 轻量关键词检索（MVP，无需 torch / 向量库） ------------------
    @staticmethod
    def keyword_retrieve(query: str, materials: list, top_k: int = 3) -> list:
        """基于关键词重叠的资料检索（Phase 5 U3 MVP）。

        不依赖 embedding 模型，纯离线可用；对中文做简单的二元组(n-gram)重叠打分。
        materials 为 Material 对象或 dict（含 id/title/content）。
        返回 [{id, title, score, snippet}] 按相关度降序。
        """
        import re

        def tokenize(text: str) -> set:
            text = (text or '').lower()
            # 中文按 2-gram 切，英文按单词切
            grams = set(re.findall(r'[\u4e00-\u9fff]', text))
            for m in re.findall(r'[a-z0-9]+', text):
                grams.add(m)
            # 中文二元组
            cn = re.findall(r'[\u4e00-\u9fff]{2,}', text)
            for w in cn:
                for i in range(len(w) - 1):
                    grams.add(w[i:i + 2])
            return grams

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scored = []
        for mat in materials:
            if isinstance(mat, dict):
                mid = mat.get('id')
                title = mat.get('title', '')
                content = mat.get('content', '')
            else:
                mid, title, content = mat.id, mat.title, mat.content
            mat_tokens = tokenize(title + '\n' + content)
            overlap = len(q_tokens & mat_tokens)
            if overlap == 0:
                continue
            score = round(overlap / (len(q_tokens | mat_tokens) or 1), 3)
            snippet = (content or '')[:120]
            scored.append({'id': mid, 'title': title, 'score': score, 'snippet': snippet})

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]