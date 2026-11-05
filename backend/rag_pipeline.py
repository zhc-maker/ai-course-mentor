"""
RAG 全流程管道 - 串联文档解析、分块、向量化、存储、检索

使用方式:
    rag = RAGPipeline()
    rag.build_knowledge_base('knowledge_base/')    # 从目录构建知识库
    answer = rag.query('什么是 QLoRA？')             # 检索 + 构造 prompt
"""

import os
import sys
import glob
from typing import List, Tuple

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_parser import parse, SUPPORTED_EXTENSIONS
from chunker import chunk_text
from embedder import Embedder
from vector_store import VectorStore

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledge_base')


class RAGPipeline:
    """RAG 检索增强生成全流程"""

    def __init__(self, kb_dir: str = None, top_k: int = 3):
        self.kb_dir = kb_dir or KB_DIR
        self.top_k = top_k
        self.embedder: Embedder | None = None
        self.vector_store: VectorStore | None = None
        self._initialized = False

    def _ensure_initialized(self):
        """延迟初始化：先加载 embedding 模型，再尝试加载已有索引"""
        if self._initialized:
            return
        self.embedder = Embedder()
        dim = self.embedder.dim
        # 尝试从磁盘加载
        self.vector_store = VectorStore.load(dim)
        if self.vector_store is None:
            self.vector_store = VectorStore(dim)
        self._initialized = True

    # ================================================================
    #  构建知识库
    # ================================================================

    def build_knowledge_base(self, kb_dir: str = None):
        """
        扫描知识库目录，解析所有支持的文件，分块，向量化，存入索引。

        Args:
            kb_dir: 知识库目录，默认使用构造时传入的路径
        """
        self._ensure_initialized()
        directory = kb_dir or self.kb_dir

        # 1. 扫描文件
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(glob.glob(os.path.join(directory, f'*{ext}')))
            files.extend(glob.glob(os.path.join(directory, f'*{ext.upper()}')))

        files = sorted(set(files))
        if not files:
            print(f'[RAG] 警告: 知识库目录 {directory} 中未找到支持的文件')
            print(f'[RAG] 支持格式: {", ".join(SUPPORTED_EXTENSIONS)}')
            return 0

        print(f'[RAG] 找到 {len(files)} 个文件')

        all_chunks = []

        for fpath in files:
            fname = os.path.basename(fpath)
            print(f'[RAG]   解析: {fname} ...')
            try:
                text = parse(fpath)
                # 附加文件来源信息
                text = f'[来源: {fname}]\n\n{text}'
                chunks = chunk_text(text)
                print(f'[RAG]   分块: {len(chunks)} 块')
                all_chunks.extend(chunks)
            except Exception as e:
                print(f'[RAG]   错误: {fname} - {e}')

        if not all_chunks:
            print('[RAG] 警告: 没有解析到任何有效内容')
            return 0

        print(f'[RAG] 总计 {len(all_chunks)} 个文本块，开始向量化 ...')

        # 2. 向量化
        vectors = self.embedder.encode(all_chunks, show_progress=True)

        # 3. 存入索引
        self.vector_store = VectorStore(self.embedder.dim)
        self.vector_store.add(vectors, all_chunks)

        # 4. 持久化
        self.vector_store.save()
        print(f'[RAG] 知识库构建完成: {self.vector_store.size} 条向量')

        return self.vector_store.size

    # ================================================================
    #  检索
    # ================================================================

    def search(self, query: str, top_k: int = None) -> List[Tuple[str, float]]:
        """
        根据查询检索最相关的文本块。

        Args:
            query: 查询文本
            top_k: 返回数量（默认使用构造时的值）

        Returns:
            [(文本块, 相似度分数), ...]
        """
        self._ensure_initialized()
        if self.vector_store.size == 0:
            raise RuntimeError('知识库为空，请先调用 build_knowledge_base()')

        k = top_k or self.top_k
        query_vec = self.embedder.encode_single(query)
        return self.vector_store.search(query_vec, top_k=k)

    # ================================================================
    #  构造增强 prompt
    # ================================================================

    def build_prompt(self, query: str) -> str:
        """
        检索 + 构造注入知识的 prompt。

        Args:
            query: 用户问题

        Returns:
            拼接了检索结果的完整 prompt 文本
        """
        results = self.search(query)

        if not results:
            return (
                '你是一个课程咨询助手。用户问了一个问题，但知识库中没有找到相关内容。\n'
                '请如实告知用户你暂时无法回答这个问题，并建议用户上传相关课程资料。\n\n'
                f'用户问题: {query}'
            )

        # 拼接检索结果
        context_parts = []
        for i, (text, score) in enumerate(results, 1):
            # 截断过长的文本块
            snippet = text[:800] + '...' if len(text) > 800 else text
            context_parts.append(f'[参考资料 {i} (相似度: {score:.2f})]\n{snippet}')

        context = '\n\n---\n\n'.join(context_parts)

        prompt = (
            '你是一个专业的课程咨询助手，名字叫 AI Engineer Mentor。\n'
            '请根据以下参考资料回答用户的问题。\n'
            '如果参考资料不足以回答，请如实说明，不要编造。\n'
            '回答要简洁、有条理。\n\n'
            f'{context}\n\n'
            f'---\n\n'
            f'用户问题: {query}\n\n'
            f'请回答:'
        )

        return prompt

    # ================================================================
    #  查询（返回结构化结果）
    # ================================================================

    def query(self, question: str) -> dict:
        """
        完整查询接口，返回包含检索结果和 prompt 的结构化数据。

        Returns:
            {
                'results': [(text, score), ...],
                'prompt': str,
                'has_context': bool,
            }
        """
        results = self.search(question)
        prompt = self.build_prompt(question)
        return {
            'results': results,
            'prompt': prompt,
            'has_context': len(results) > 0,
        }


# ============================================================
#  自测
# ============================================================

if __name__ == '__main__':
    print('=' * 60)
    print('RAG Pipeline 自测')
    print('=' * 60)

    rag = RAGPipeline()

    # 构建知识库
    print('\n>>> 构建知识库 ...')
    rag.build_knowledge_base()

    # 测试查询
    questions = [
        '什么是 QLoRA？',
        '深度学习有哪些激活函数？',
        '今天天气怎么样？',  # 知识库外的无关问题
    ]
    for q in questions:
        print(f'\n{"=" * 60}')
        print(f'>>> 查询: {q}')
        result = rag.query(q)
        print(f'检索到 {len(result["results"])} 条参考资料:')
        for text, score in result['results']:
            print(f'  [{score:.3f}] {text[:100]}...')
        print(f'\n>>> 生成 Prompt（前 300 字符）:')
        print(result['prompt'][:300])
