import os
import re
import json
import logging
import threading
from typing import List, Dict, Optional, Any, Callable

logger = logging.getLogger(__name__)

# 配置优先取 app.config（Phase 8 在 config.py 中定义），缺失时回退 env / 默认值，
# 以保证本模块可独立导入（测试、脚本场景）。
try:
    from app.config import (
        RAG_EMBEDDING_MODEL as _M,
        RAG_CHUNK_SIZE as _CS,
        RAG_CHUNK_OVERLAP as _CO,
        RAG_TOP_K as _TK,
        RAG_SIM_THRESHOLD as _TH,
        RAG_INDEX_DIR as _ID,
    )
except Exception:  # pragma: no cover - 配置尚未就绪时的兜底
    _M = _CS = _CO = _TK = _TH = _ID = None

DEFAULT_MODEL = _M or os.getenv('RAG_EMBEDDING_MODEL', 'shibing624/text2vec-base-chinese')
CHUNK_SIZE = int(_CS if _CS is not None else os.getenv('RAG_CHUNK_SIZE', '400'))
CHUNK_OVERLAP = int(_CO if _CO is not None else os.getenv('RAG_CHUNK_OVERLAP', '80'))
TOP_K = int(_TK if _TK is not None else os.getenv('RAG_TOP_K', '4'))
SIM_THRESHOLD = float(_TH if _TH is not None else os.getenv('RAG_SIM_THRESHOLD', '0.25'))
INDEX_DIR = _ID or os.getenv('RAG_INDEX_DIR') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'data', 'rag'
)


def _tokenize(text: str) -> set:
    """中文按字符 + 二元组切，英文按单词切。"""
    text = (text or '').lower()
    grams = set(re.findall(r'[\u4e00-\u9fff]', text))
    for m in re.findall(r'[a-z0-9]+', text):
        grams.add(m)
    cn = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    for w in cn:
        for i in range(len(w) - 1):
            grams.add(w[i:i + 2])
    return grams


class RAGService:
    """RAG 知识库服务（Phase 8 实装：向量检索 + 磁盘持久化 + 关键词兜底）。

    设计要点：
    - 向量化默认用 sentence-transformers（首个模型名来自 env RAG_EMBEDDING_MODEL，
      默认中文向量模型），加载失败或不可用时自动回退到关键词检索。
    - 支持注入 embedder（测试用确定性向量函数），无需 torch 即可验证完整管线。
    - 每用户：内存缓存 + 磁盘持久化（FAISS 索引优先，不可用时存 numpy .npy）。
    - 检索返回 [{material_id, title, score, snippet, content}]，供 RAG 生成使用。
    """

    def __init__(
        self,
        embedder: Optional[Callable[[List[str]], Any]] = None,
        model_name: Optional[str] = None,
        index_dir: Optional[str] = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        top_k: int = TOP_K,
        threshold: float = SIM_THRESHOLD,
    ):
        self._embedder = embedder  # 可注入；None 则懒加载 sentence_transformers
        self._model_name = model_name or DEFAULT_MODEL
        self._index_dir = index_dir or INDEX_DIR
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.threshold = threshold
        self._np = None
        self._vector_capable = embedder is not None
        self._lock = threading.Lock()
        self._cache: Dict[int, dict] = {}

    # --------------------------- 向量化 ---------------------------
    def _ensure_np(self):
        if self._np is None:
            import numpy as np
            self._np = np
        return self._np

    def _get_embedder(self):
        """返回可调用 embedder(texts)->matrix；向量不可用则返回 None。"""
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self._np = np
            model = SentenceTransformer(self._model_name)
            # 归一化后内积即余弦相似度
            self._embedder = lambda texts: model.encode(
                texts, normalize_embeddings=True
            )
            self._vector_capable = True
            logger.info(f'Embedding 模型加载成功：{self._model_name}')
            return self._embedder
        except Exception as e:
            logger.warning(f'向量模型加载失败，RAG 回退关键词检索：{e}')
            self._embedder = None
            self._vector_capable = False
            return None

    def _embed(self, texts):
        emb = self._get_embedder()
        if emb is None:
            return None
        return emb(texts)

    # --------------------------- 文本分块 ---------------------------
    def _chunk_text(self, content: str) -> List[str]:
        """中文感知分块：先按段落，超长段落按滑动窗口切，带重叠。"""
        content = (content or '').strip()
        if not content:
            return []
        paras = [p.strip() for p in re.split(r'\r?\n+', content) if p.strip()]
        chunks: List[str] = []
        buf = ''
        for p in paras:
            if len(buf) + len(p) + 1 <= self.chunk_size:
                buf = (buf + '\n' + p).strip() if buf else p
            else:
                if buf:
                    chunks.append(buf)
                if len(p) > self.chunk_size:
                    step = max(1, self.chunk_size - self.chunk_overlap)
                    for i in range(0, len(p), step):
                        seg = p[i:i + self.chunk_size]
                        if seg.strip():
                            chunks.append(seg)
                    buf = ''
                else:
                    buf = p
        if buf:
            chunks.append(buf)
        return chunks

    # --------------------------- 索引构建 / 持久化 ---------------------------
    def _build_entry(self, user_id, materials):
        """materials: list of (id, title, content)。构建并持久化索引。"""
        records = []
        texts = []
        for mid, title, content in materials:
            for txt in self._chunk_text(content):
                records.append({'material_id': mid, 'title': title, 'text': txt})
                texts.append(txt)

        mode = 'keyword'
        matrix = None
        emb = self._get_embedder()
        if emb is not None and texts:
            np = self._ensure_np()
            matrix = np.asarray(emb(texts), dtype='float32')
            if matrix.ndim == 2 and matrix.shape[0] > 0:
                mode = 'vector'

        entry = {'chunks': records, 'matrix': matrix, 'mode': mode, 'model': self._model_name}
        self._persist(user_id, entry)
        with self._lock:
            self._cache[user_id] = entry
        return entry

    def _paths(self, user_id):
        base = os.path.join(self._index_dir, str(user_id))
        return base + '.meta.json', base + '.index', base + '.npy'

    def _persist(self, user_id, entry):
        try:
            os.makedirs(self._index_dir, exist_ok=True)
            meta_path, index_path, npy_path = self._paths(user_id)
            fmt = 'none'
            if entry['mode'] == 'vector' and entry['matrix'] is not None:
                np = self._ensure_np()
                matrix = np.asarray(entry['matrix'], dtype='float32')
                try:
                    import faiss
                    index = faiss.IndexFlatIP(matrix.shape[1])
                    index.add(matrix)
                    faiss.write_index(index, index_path)
                    fmt = 'faiss'
                except Exception:
                    np.save(npy_path, matrix)
                    fmt = 'numpy'
            meta = {
                'mode': entry['mode'],
                'model': entry.get('model'),
                'matrix_format': fmt,
                'chunks': entry['chunks'],
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f'RAG 索引持久化失败（仅保留内存）：{e}')

    def _load(self, user_id):
        meta_path, index_path, npy_path = self._paths(user_id)
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            chunks = meta.get('chunks', [])
            matrix = None
            if meta.get('mode') == 'vector':
                fmt = meta.get('matrix_format')
                if fmt == 'faiss' and os.path.exists(index_path):
                    try:
                        import faiss
                        index = faiss.read_index(index_path)
                        matrix = self._faiss_to_matrix(index)
                    except Exception as e:
                        logger.warning(f'faiss 索引读取失败，尝试 numpy：{e}')
                if matrix is None and os.path.exists(npy_path):
                    np = self._ensure_np()
                    matrix = np.load(npy_path)
            return {'chunks': chunks, 'matrix': matrix, 'mode': meta.get('mode'), 'model': meta.get('model')}
        except Exception as e:
            logger.warning(f'RAG 索引读取失败：{e}')
            return None

    def _faiss_to_matrix(self, index):
        np = self._ensure_np()
        if hasattr(index, 'reconstruct_n'):
            return index.reconstruct_n(0, index.ntotal)
        n = index.ntotal
        out = np.empty((n, index.d), dtype='float32')
        for i in range(n):
            out[i] = index.reconstruct(i)
        return out

    # --------------------------- 对外 API ---------------------------
    def _load_materials_from_db(self, user_id):
        try:
            from models.material import Material
            mats = Material.query.filter_by(user_id=user_id).all()
            return [(m.id, m.title, m.content) for m in mats]
        except Exception as e:
            logger.warning(f'从数据库加载资料失败（可能无应用上下文）：{e}')
            return []

    def _ensure(self, user_id):
        with self._lock:
            if user_id in self._cache:
                return self._cache[user_id]
        entry = self._load(user_id)
        if entry is not None:
            with self._lock:
                self._cache[user_id] = entry
            return entry
        materials = self._load_materials_from_db(user_id)
        if materials:
            return self._build_entry(user_id, materials)
        return None

    def retrieve(self, user_id, query: str, top_k: int = None, threshold: float = None) -> List[Dict]:
        """向量检索相关资料；向量不可用 / 失败时回退关键词。"""
        top_k = top_k or self.top_k
        threshold = threshold if threshold is not None else self.threshold
        entry = self._ensure(user_id)
        if not entry or not entry['chunks']:
            return []

        if entry['mode'] == 'vector' and entry['matrix'] is not None:
            try:
                np = self._ensure_np()
                q = np.asarray(self._embed([query])[0], dtype='float32')
                matrix = np.asarray(entry['matrix'], dtype='float32')
                scores = matrix @ q
                order = np.argsort(-scores)
                out = []
                for i in order[:top_k]:
                    i = int(i)
                    if float(scores[i]) < threshold:
                        continue
                    c = entry['chunks'][i]
                    out.append({
                        'material_id': c['material_id'],
                        'title': c['title'],
                        'score': round(float(scores[i]), 4),
                        'snippet': c['text'][:160],
                        'content': c['text'],
                    })
                return out
            except Exception as e:
                logger.warning(f'向量检索失败，回退关键词：{e}')

        return self._keyword_search(entry['chunks'], query, top_k)

    def rebuild(self, user_id, materials: List[tuple] = None) -> dict:
        """显式重建索引。materials 为 [(id, title, content)]；省略则从 DB 读取。"""
        if materials is None:
            materials = self._load_materials_from_db(user_id)
        return self._build_entry(user_id, materials)

    def invalidate(self, user_id):
        """使某用户的索引失效（资料变更后调用，下次查询自动重建）。"""
        with self._lock:
            self._cache.pop(user_id, None)
        for ext in ('.meta.json', '.index', '.npy'):
            p = os.path.join(self._index_dir, f'{user_id}{ext}')
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def status(self, user_id) -> Dict:
        entry = self._cache.get(user_id)
        if entry is None:
            entry = self._load(user_id)
        if entry is None:
            return {
                'indexed': False,
                'chunk_count': 0,
                'mode': None,
                'model': self._model_name,
                'vector_available': self._vector_capable,
            }
        return {
            'indexed': True,
            'chunk_count': len(entry['chunks']),
            'mode': entry['mode'],
            'model': entry.get('model'),
            'vector_available': entry['mode'] == 'vector',
        }

    # --------------------------- 关键词兜底 ---------------------------
    def _keyword_search(self, chunks: List[Dict], query: str, top_k: int) -> List[Dict]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored = []
        for c in chunks:
            mat_tokens = _tokenize(c['title'] + '\n' + c['text'])
            overlap = len(q_tokens & mat_tokens)
            if overlap == 0:
                continue
            score = round(overlap / (len(q_tokens | mat_tokens) or 1), 3)
            scored.append({
                'material_id': c['material_id'],
                'title': c['title'],
                'score': score,
                'snippet': c['text'][:160],
                'content': c['text'],
            })
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]

    @staticmethod
    def keyword_retrieve(query: str, materials: list, top_k: int = 3) -> list:
        """基于关键词重叠的资料检索（离线 MVP，兼容旧调用）。

        materials 为 Material 对象或 dict（含 id/title/content）。
        返回 [{id, title, score, snippet}] 按相关度降序。
        """
        chunks = []
        for mat in materials:
            if isinstance(mat, dict):
                mid = mat.get('id')
                title = mat.get('title', '')
                content = mat.get('content', '')
            else:
                mid, title, content = mat.id, mat.title, mat.content
            chunks.append({'material_id': mid, 'title': title, 'text': content})
        scored = []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        for c in chunks:
            mat_tokens = _tokenize(c['title'] + '\n' + c['text'])
            overlap = len(q_tokens & mat_tokens)
            if overlap == 0:
                continue
            score = round(overlap / (len(q_tokens | mat_tokens) or 1), 3)
            scored.append({'id': c['material_id'], 'title': c['title'], 'score': score,
                           'snippet': (c['text'] or '')[:120]})
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]
