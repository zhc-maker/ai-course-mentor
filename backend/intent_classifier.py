"""
意图识别模块 - 高精度三分类

使用 embedding 原型向量做相似度匹配，准确率目标 98%+
类别: RAG / WEB / CHAT
"""

import numpy as np
from typing import Tuple

# ============================================================
#  每个类别的原型问句库（越多越准）
# ============================================================

RAG_PROTOTYPES = [
    # 深度学习基础
    "什么是深度学习？", "神经网络有哪些层？", "激活函数有哪几种？",
    "什么是反向传播？", "损失函数的作用是什么？", "优化器有哪些？",
    # PyTorch
    "PyTorch 怎么用？", "什么是张量？", "怎么用 GPU 训练模型？",
    "DataLoader 怎么用？", "nn.Module 是什么？",
    # LLM
    "什么是大语言模型？", "GPT 和 LLaMA 有什么区别？", "Transformer 架构是什么？",
    "什么是注意力机制？", "QLoRA 是什么？", "怎么微调大模型？",
    # RAG
    "RAG 是什么？", "怎么做知识检索？", "什么是向量数据库？",
    "embedding 怎么用？", "FAISS 是什么？", "chunking 怎么做？",
    # 课程相关
    "课程有多少章节？", "A3 项目怎么做？", "作业要求是什么？",
    "去哪里下载课件？", "考试范围是什么？", "学完需要多久？",
]

WEB_PROTOTYPES = [
    # 天气
    "今天天气怎么样？", "明天会下雨吗？", "上海气温多少度？",
    # 新闻
    "最近有什么新闻？", "今天发生了什么大事？",
    # 股价/金融
    "特斯拉股价多少？", "比特币价格？", "美元汇率是多少？",
    # 实时信息
    "现在几点？", "2024 年奥运会谁赢了？", "最新 AI 进展有哪些？",
    "Python 最新版本是什么？", "PyTorch 最新版本号？",
    # 人物/事件查询
    "某某明星是谁？", "某某电影的导演是谁？", "某某公司的 CEO 是谁？",
]

CHAT_PROTOTYPES = [
    # 问候
    "你好", "嗨", "Hello", "早上好", "晚上好",
    # 身份
    "你是谁？", "你叫什么名字？", "你能做什么？",
    # 闲聊
    "谢谢", "再见", "好的", "明白了",
    "讲个笑话", "你会什么？", "介绍一下你自己",
    # 无意义
    "嗯", "哦", "哈哈", "。。。",
    # 情感
    "今天心情不好", "我很难过", "好开心啊",
]


# ============================================================
#  分类器
# ============================================================

class IntentClassifier:
    """基于 embedding 原型向量的意图分类器"""

    def __init__(self):
        self._embedder = None
        self._prototype_centroids = {}  # {"rag": np.array, "web": ..., "chat": ...}
        self._fitted = False
        self._primary_threshold = 0.35  # 低于此值用 LLM 二次判断

    @property
    def embedder(self):
        """延迟加载 embedding 模型（复用现有 embedder.py）"""
        if self._embedder is None:
            from embedder import Embedder
            self._embedder = Embedder()
        return self._embedder

    def fit(self):
        """预计算各分类的原型中心向量"""
        if self._fitted:
            return

        print('[IntentClassifier] 计算原型向量 ...')
        categories = {
            'rag': RAG_PROTOTYPES,
            'web': WEB_PROTOTYPES,
            'chat': CHAT_PROTOTYPES,
        }
        for name, prototypes in categories.items():
            vecs = self.embedder.encode(prototypes)
            self._prototype_centroids[name] = vecs.mean(axis=0)  # 中心向量
            # 归一化
            norm = np.linalg.norm(self._prototype_centroids[name])
            if norm > 0:
                self._prototype_centroids[name] /= norm

        self._fitted = True
        # 归一化阈值：二分类之间的最小差距
        self._margin = 0.02  # rag vs web 差距小于此值用 LLM 判断
        print('[IntentClassifier] 原型向量计算完成')

    def _keyword_prefilter(self, query: str) -> Tuple[bool, str]:
        """关键词预筛选"""
        q = query.strip().lower()

        # ---- 先检查 RAG 关键词（课程/技术/AI/学习相关） ----
        rag_keywords = [
            '课程', '学习', '知识', 'ai', '代码', 'python', 'pytorch', '技术',
            '模型', '训练', '微调', '架构', '网络', '算法', '框架', '函数',
            '什么是', '是什么', '怎么', '如何', '介绍', '讲讲', '解释',
            '深度学习', '机器学习', 'llm', 'rag', 'qlora', 'transformer',
            '编程', '开发', '教程', '章', '讲', '课件', '资料', '内容',
            '激活函数', '损失', '优化器', '梯度', '反向传播', '注意力',
        ]
        web_only_keywords = ['天气', '新闻', '股价', '价格', '热搜', '最新版本']

        has_rag = any(kw in q for kw in rag_keywords)
        has_web = any(kw in q for kw in web_only_keywords)

        if has_rag and not has_web:
            return (True, 'rag')
        if has_web:
            return (True, 'web')

        # ---- 纯聊天短语 ----
        chat_patterns = [
            '你好', '嗨', 'hello', 'hi', '早上好', '晚上好', '下午好',
            '谢谢', '再见', '拜拜', 'bye', '好的', 'ok', '嗯', '哦', '哈哈',
            '你是谁', '你叫什么', '你是干什么的', '你能做什么', '什么是你',
            '介绍一下你自己', '你会什么', '讲个笑话', '讲笑话',
        ]
        for p in chat_patterns:
            if p in q:
                return (True, 'chat')
        # 极短输入默认 chat
        if len(q) <= 3 and not (has_rag or has_web):
            return (True, 'chat')
        return (False, '')

    def classify(self, query: str, use_llm_fallback: bool = True) -> Tuple[str, float, dict]:
        """
        分类用户意图。

        Returns:
            (category, confidence, details)
        """
        if not self._fitted:
            self.fit()

        # 0. 关键词预筛选
        match, cat = self._keyword_prefilter(query)
        if match:
            return (cat, 1.0, {'scores': {}, 'method': 'keyword'})

        # 1. 计算 query 向量
        qvec = self.embedder.encode_single(query)

        # 2. 与每个类别中心计算余弦相似度
        scores = {}
        for name, centroid in self._prototype_centroids.items():
            sim = float(np.dot(qvec, centroid))
            scores[name] = sim

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # 3. rag vs web 差距太小 → LLM 二次判断
        rag_score = scores.get('rag', 0)
        web_score = scores.get('web', 0)
        if use_llm_fallback and abs(rag_score - web_score) < self._margin:
            llm_category = self._llm_classify(query)
            if llm_category:
                return (llm_category, 0.85, {
                    'scores': scores,
                    'method': 'llm_fallback',
                    'embedding_best': best_category,
                })

        # 4. 置信度低于阈值 → LLM 二次判断
        if use_llm_fallback and best_score < self._primary_threshold:
            llm_category = self._llm_classify(query)
            if llm_category:
                return (llm_category, 0.85, {
                    'scores': scores,
                    'method': 'llm_fallback',
                    'embedding_best': best_category,
                })

        return (best_category, best_score, {
            'scores': scores,
            'method': 'embedding',
        })

    def _llm_classify(self, query: str) -> str | None:
        """LLM 二次判断（embedding 置信度低时使用）"""
        try:
            from llm import LLM
            if not hasattr(self, '_llm'):
                self._llm = LLM()

            prompt = (
                '请判断以下用户问题的意图，只回复一个词：rag, web, chat。\n'
                '- rag: 关于课程、AI、编程、技术学习等知识问答\n'
                '- web: 需要联网获取实时信息（天气、新闻、股价、最新版本等）\n'
                '- chat: 一般闲聊、问候、身份询问\n\n'
                f'用户问题: "{query}"\n意图:'
            )
            result = self._llm.chat(prompt, max_new_tokens=10, temperature=0.1)

            for cat in ['rag', 'web', 'chat']:
                if cat in result.lower():
                    return cat
            return None
        except Exception:
            return None


# ============================================================
#  自测
# ============================================================

if __name__ == '__main__':
    classifier = IntentClassifier()
    classifier.fit()

    test_cases = [
        ("什么是 QLoRA？", "rag"),
        ("怎么用 PyTorch 训练模型？", "rag"),
        ("今天天气怎么样？", "web"),
        ("比特币最新价格", "web"),
        ("你好", "chat"),
        ("你是谁", "chat"),
        ("深度学习有哪些激活函数", "rag"),
        ("最近 AI 领域有什么大新闻", "web"),
    ]

    correct = 0
    for query, expected in test_cases:
        cat, conf, details = classifier.classify(query, use_llm_fallback=False)
        ok = "OK" if cat == expected else "MISS"
        if cat == expected:
            correct += 1
        print(f'  [{ok}] "{query}" → {cat} (conf={conf:.3f}, expected={expected})')
        if details['method'] != 'embedding':
            print(f'         method={details["method"]}')

    acc = correct / len(test_cases) * 100
    print(f'\n准确率: {acc:.1f}% ({correct}/{len(test_cases)})')
