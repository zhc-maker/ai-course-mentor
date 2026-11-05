"""
Embedding 模块 - 将文本转换为向量表示
支持多种后端：SentenceTransformer (HF/ModelScope) / TF-IDF 兜底
"""

import os
import numpy as np
from typing import List

# 模型配置
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'  # HF 模型名
MODELSCOPE_MODEL = 'iic/nlp_corom_sentence-embedding_chinese-base'
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'embedding')

# HF 镜像（国内用户）
HF_MIRROR = 'https://hf-mirror.com'


class Embedder:
    """文本向量化器 - 多后端支持"""

    def __init__(self, model_name: str = None, use_tfidf_fallback: bool = True):
        self._use_tfidf_fallback = use_tfidf_fallback
        self.model_name = model_name or self._find_best_model()
        self._model = None
        self._tfidf_vectorizer = None
        self._dim = None

    def _find_best_model(self) -> str:
        """按优先级查找可用模型"""
        # 1. 明确指定的模型名/路径
        if os.path.isdir(MODEL_NAME):
            return MODEL_NAME

        # 2. 查找 ModelScope 缓存目录中的模型
        for root, dirs, files in os.walk(LOCAL_MODEL_DIR):
            if 'pytorch_model.bin' in files and 'config.json' in files:
                print(f'[Embedder] 找到 ModelScope 模型: {root}')
                return root

        # 3. 查找 HF 缓存中的模型
        cache_home = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
        if os.path.isdir(cache_home):
            for root, dirs, files in os.walk(cache_home):
                if 'MiniLM' in root and 'config_sentence_transformers.json' in files:
                    print(f'[Embedder] HF 缓存模型: {root}')
                    return root

        # 3. 全部失败，使用 TF-IDF 兜底
        if self._use_tfidf_fallback:
            print('[Embedder] 使用 TF-IDF 兜底方案')
            print('[Embedder] 提示: 运行 python backend/download_model.py 下载完整模型以提升精度')
            return '__tfidf__'
        raise RuntimeError(
            '无法加载 embedding 模型。请先运行: python backend/download_model.py\n'
        )

    @property
    def dim(self) -> int:
        """向量维度"""
        if self._dim is None:
            if self.model_name == '__tfidf__':
                self._dim = 128  # TF-IDF 降维后维度
            else:
                self._dim = self._st_model.get_sentence_embedding_dimension()
        return self._dim

    @property
    def _st_model(self):
        """SentenceTransformer 模型（延迟加载）"""
        if self._model is None and self.model_name != '__tfidf__':
            from sentence_transformers import SentenceTransformer
            print(f'[Embedder] 加载模型: {self.model_name} ...')
            self._model = SentenceTransformer(self.model_name)
            print(f'[Embedder] 模型已加载, 维度: {self._model.get_sentence_embedding_dimension()}')
        return self._model

    @property
    def _tfidf(self):
        """TF-IDF 向量化器（兜底方案）"""
        if self._tfidf_vectorizer is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            # TF-IDF 不依赖预训练模型，但需要先 fit
            self._tfidf_vectorizer = TfidfVectorizer(max_features=5000)
            self._tfidf_svd = TruncatedSVD(n_components=128)
            self._tfidf_fitted = False
        return self._tfidf_vectorizer

    def encode(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """文本转向量"""
        if not texts:
            return np.array([])

        if self.model_name == '__tfidf__':
            return self._encode_tfidf(texts)
        else:
            embeddings = self._st_model.encode(
                texts,
                show_progress_bar=show_progress,
                normalize_embeddings=True,
            )
            return np.array(embeddings)

    def _encode_tfidf(self, texts: List[str]) -> np.ndarray:
        """TF-IDF 向量化（仅用于演示/测试，精度低于 SentenceTransformer）"""
        from sklearn.decomposition import TruncatedSVD
        vec = self._tfidf

        if not self._tfidf_fitted:
            sparse = vec.fit_transform(texts)
            self._tfidf_fitted = True
            # 降维到 128
            self._tfidf_svd.fit(sparse.toarray() if sparse.shape[0] >= 128 else np.zeros((128, 5000)))
        else:
            sparse = vec.transform(texts)

        dense = sparse.toarray()
        # 如果没 fit 过 SVD 或文本太少，直接截断/填充
        if dense.shape[1] > self.dim:
            svd = self._tfidf_svd
            dense = svd.transform(dense)
        elif dense.shape[1] < self.dim:
            dense = np.pad(dense, ((0, 0), (0, self.dim - dense.shape[1])))

        # 归一化
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return dense / norms

    def encode_single(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


if __name__ == '__main__':
    emb = Embedder()
    texts = [
        '深度学习是机器学习的一个分支',
        'PyTorch 是一个深度学习框架',
        '我喜欢吃披萨',
    ]
    vecs = emb.encode(texts)
    print(f'后端: {emb.model_name}')
    print(f'向量形状: {vecs.shape}')
    sim_0_1 = np.dot(vecs[0], vecs[1])
    sim_0_2 = np.dot(vecs[0], vecs[2])
    print(f'相似度(0,1): {sim_0_1:.4f}  (同类应较高)')
    print(f'相似度(0,2): {sim_0_2:.4f}  (异类应较低)')
