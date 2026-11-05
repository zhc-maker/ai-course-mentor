"""
向量存储模块 - 基于 FAISS 的本地向量索引

支持:
- 添加向量（批量）
- 相似度检索（Top-K）
- 保存/加载索引到磁盘
- 关联文本元数据（检索时返回原文片段）
"""

import os
import json
import numpy as np
from typing import List, Tuple, Optional

INDEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vector_index')


class VectorStore:
    """基于 FAISS 的向量存储"""

    def __init__(self, dim: int):
        self.dim = dim
        self.index = None
        self.texts: List[str] = []   # 与向量一一对应的原始文本
        self._init_index()

    def _init_index(self):
        """初始化 FAISS 索引（内积搜索，配合归一化向量 = 余弦相似度）"""
        import faiss
        self.index = faiss.IndexFlatIP(self.dim)  # Inner Product

    def add(self, vectors: np.ndarray, texts: List[str]):
        """
        批量添加向量和对应文本。

        Args:
            vectors: shape=(n, dim)
            texts: 长度为 n 的文本列表
        """
        if len(vectors) == 0:
            return
        vectors = np.array(vectors, dtype=np.float32)
        self.index.add(vectors)
        self.texts.extend(texts)

    def search(self, query_vec: np.ndarray, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        检索与查询向量最相似的 top_k 个文本。

        Args:
            query_vec: shape=(dim,) 的查询向量
            top_k: 返回数量

        Returns:
            [(文本, 相似度分数), ...]，按分数降序
        """
        if self.index.ntotal == 0:
            return []
        query_vec = np.array([query_vec], dtype=np.float32)
        scores, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.texts):
                results.append((self.texts[idx], float(score)))
        return results

    @property
    def size(self) -> int:
        """当前索引中的向量数量"""
        return self.index.ntotal if self.index else 0

    def save(self, dir_path: str = None):
        """保存索引和文本映射到磁盘"""
        import faiss
        save_dir = dir_path or INDEX_DIR
        os.makedirs(save_dir, exist_ok=True)

        index_path = os.path.join(save_dir, 'faiss_index.bin')
        texts_path = os.path.join(save_dir, 'texts.json')

        faiss.write_index(self.index, index_path)
        with open(texts_path, 'w', encoding='utf-8') as f:
            json.dump(self.texts, f, ensure_ascii=False)

        print(f'[VectorStore] 索引已保存: {save_dir} ({self.size} 条)')

    @classmethod
    def load(cls, dim: int, dir_path: str = None) -> Optional['VectorStore']:
        """从磁盘加载索引"""
        import faiss
        load_dir = dir_path or INDEX_DIR
        index_path = os.path.join(load_dir, 'faiss_index.bin')
        texts_path = os.path.join(load_dir, 'texts.json')

        if not os.path.exists(index_path) or not os.path.exists(texts_path):
            return None

        store = cls(dim)
        store.index = faiss.read_index(index_path)
        with open(texts_path, 'r', encoding='utf-8') as f:
            store.texts = json.load(f)
        print(f'[VectorStore] 索引已加载: {load_dir} ({store.size} 条)')
        return store


if __name__ == '__main__':
    # 自测
    dim = 384  # MiniLM 的向量维度
    store = VectorStore(dim)
    vecs = np.random.randn(5, dim).astype(np.float32)
    texts = [f'文档片段 {i}' for i in range(5)]
    store.add(vecs, texts)
    print(f'索引大小: {store.size}')
    query = np.random.randn(dim).astype(np.float32)
    results = store.search(query, top_k=3)
    for text, score in results:
        print(f'  {text}: 相似度 {score:.4f}')
