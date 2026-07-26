"""Phase 8 RAG 向量检索测试（注入确定性 embedder，不依赖 torch / 联网）。"""
import numpy as np
import tempfile

from ai.rag import RAGService


def _make_embedder(dim=64):
    """维度恒定（与输入集合无关）的确定性 embedder，便于无 torch 验证完整管线。"""
    def embed(texts):
        M = []
        for t in texts:
            v = np.zeros(dim, dtype='float32')
            for ch in t:
                v[ord(ch) % dim] += 1
            M.append(v)
        return np.array(M, dtype='float32')
    return embed


MATS = [
    (1, '线性代数笔记', '矩阵 特征值 特征向量 很重要'),
    (2, '英语阅读', '英语 词汇 阅读理解 积累'),
]


def test_vector_retrieve_top_relevant():
    svc = RAGService(embedder=_make_embedder(), index_dir=tempfile.mkdtemp())
    svc.rebuild(1, MATS)
    res = svc.retrieve(1, '矩阵 特征值', top_k=2)
    assert res and res[0]['material_id'] == 1
    assert 'content' in res[0] and 'score' in res[0]


def test_persist_and_reload():
    idx = tempfile.mkdtemp()
    svc = RAGService(embedder=_make_embedder(), index_dir=idx)
    svc.rebuild(1, MATS)
    svc2 = RAGService(embedder=_make_embedder(), index_dir=idx)
    res = svc2.retrieve(1, '矩阵 特征值', top_k=2)
    assert res and res[0]['material_id'] == 1


def test_keyword_fallback():
    svc = RAGService(embedder=None, index_dir=tempfile.mkdtemp())
    svc._get_embedder = lambda: None  # 强制无向量，走关键词兜底
    svc.rebuild(1, MATS)
    assert svc.status(1)['mode'] == 'keyword'
    res = svc.retrieve(1, '线性代数', top_k=2)
    assert res and res[0]['material_id'] == 1


def test_invalidate_clears_index():
    idx = tempfile.mkdtemp()
    svc = RAGService(embedder=_make_embedder(), index_dir=idx)
    svc.rebuild(1, MATS)
    svc.invalidate(1)
    assert svc._load(1) is None
    assert svc.status(1)['indexed'] is False


def test_status_empty():
    svc = RAGService(embedder=_make_embedder(), index_dir=tempfile.mkdtemp())
    st = svc.status(999)
    assert st['indexed'] is False
    assert st['vector_available'] is True
