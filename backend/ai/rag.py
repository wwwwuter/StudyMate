import os
import logging
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 知识库服务"""

    def __init__(self):
        self.embedding_model = None
        self.documents = []
        self.embeddings = None
        self._model_name = 'paraphrase-multilingual-MiniLM-L12-v2'

    def _load_embedding_model(self):
        """延迟加载 embedding 模型"""
        if self.embedding_model is None:
            try:
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
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        logger.info(f'文档已添加，当前共 {len(self.documents)} 个文本块')
        return len(chunks)

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """检索相关文档"""
        if not self.documents:
            return []

        self._load_embedding_model()
        query_embedding = self.embedding_model.encode([query])

        # 计算余弦相似度
        scores = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(scores)[-top_k:][::-1]

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