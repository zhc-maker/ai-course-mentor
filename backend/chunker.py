"""
文本分块模块 - 将长文本切分为固定大小的重叠块
"""

from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separator: str = '\n',
) -> List[str]:
    """
    按段落优先、滑动窗口的方式分块。

    Args:
        text: 原始文本
        chunk_size: 每块最大字符数
        overlap: 相邻块的重叠字符数
        separator: 段落分隔符

    Returns:
        文本块列表
    """
    if not text or not text.strip():
        return []

    # 第一步：按段落切分
    paragraphs = [p.strip() for p in text.split(separator) if p.strip()]

    chunks = []
    current = ''

    for para in paragraphs:
        # 如果当前块加上新段落超过 chunk_size，先保存当前块
        if len(current) + len(para) + 1 > chunk_size and current:
            chunks.append(current)
            # 重叠：取当前块的末尾 overlap 字符作为新块的起始
            if overlap > 0 and len(current) > overlap:
                current = current[-overlap:]
            else:
                current = ''

        # 连接段落
        if current:
            current += '\n' + para
        else:
            current = para

        # 如果当前块已经接近 chunk_size，先存起来
        if len(current) >= chunk_size:
            chunks.append(current)
            current = current[-overlap:] if overlap > 0 and len(current) > overlap else ''

    # 收尾
    if current.strip():
        chunks.append(current)

    return chunks


if __name__ == '__main__':
    # 自测
    test = '\n'.join([f'这是第{i}段测试文本，用于验证分块功能是否正常工作。' * 5 for i in range(20)])
    result = chunk_text(test, chunk_size=200, overlap=30)
    print(f'原始字符数: {len(test)}')
    print(f'分块数量: {len(result)}')
    for i, c in enumerate(result):
        print(f'  chunk {i}: {len(c)} chars - {c[:60]}...')
