"""
网络搜索模块 - 基于 Tavily API

实时获取网络信息，返回结构化搜索结果
"""

import os
from typing import List, Dict


class WebSearcher:
    """Tavily 网络搜索封装"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('TAVILY_API_KEY', '')
        self._client = None

    @property
    def client(self):
        """延迟初始化 Tavily 客户端"""
        if self._client is None:
            try:
                from tavily import TavilyClient
            except ImportError:
                raise ImportError(
                    '请安装 tavily-python: pip install tavily-python\n'
                    '注册获取 API Key: https://tavily.com'
                )
            if not self.api_key:
                raise ValueError(
                    '需要设置 TAVILY_API_KEY。\n'
                    '方式一: export TAVILY_API_KEY=tvly-xxx\n'
                    '方式二: WebSearcher(api_key="tvly-xxx")'
                )
            self._client = TavilyClient(api_key=self.api_key)
        return self._client

    @property
    def available(self) -> bool:
        """检查 API 是否可用"""
        try:
            return bool(self.client)
        except Exception:
            return False

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        执行网络搜索。

        Args:
            query: 搜索问题
            max_results: 最大结果数

        Returns:
            [{"title": ..., "content": ..., "url": ...}, ...]
        """
        if not self.api_key:
            return []

        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth='basic',  # basic 更快，advanced 更准
            )
            results = []
            for item in response.get('results', []):
                results.append({
                    'title': item.get('title', ''),
                    'content': item.get('content', ''),
                    'url': item.get('url', ''),
                })
            return results
        except Exception as e:
            print(f'[WebSearcher] 搜索失败: {e}')
            return []

    def search_for_prompt(self, query: str, max_results: int = 3) -> str:
        """
        搜索并将结果格式化为可直接注入 prompt 的文本。

        Returns:
            格式化后的参考资料文本
        """
        results = self.search(query, max_results=max_results)
        if not results:
            return ''

        parts = []
        for i, r in enumerate(results, 1):
            snippet = r['content'][:500]
            parts.append(
                f'[网络资料 {i}]\n'
                f'标题: {r["title"]}\n'
                f'来源: {r["url"]}\n'
                f'内容: {snippet}'
            )

        return '\n\n'.join(parts)


if __name__ == '__main__':
    searcher = WebSearcher()
    if not searcher.api_key:
        print('=== 未设置 TAVILY_API_KEY，跳过测试 ===')
        print('请设置环境变量: export TAVILY_API_KEY=tvly-xxx')
    else:
        print('=== 网络搜索测试 ===')
        results = searcher.search('Python 最新版本', max_results=3)
        if results:
            for r in results:
                print(f'  [{r["title"]}]')
                print(f'  {r["content"][:100]}...')
                print(f'  {r["url"]}')
                print()
        else:
            print('  搜索无结果或 API 不可用')

        print('=== Prompt 格式化 ===')
        prompt_text = searcher.search_for_prompt('Python 最新版本')
        print(prompt_text[:400])
