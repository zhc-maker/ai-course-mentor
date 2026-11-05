"""
文件解析模块 - 将各种文档格式统一解析为纯文本
最低要求：txt, docx；拓展：pdf, md, pptx, ipynb, xlsx
统一接口：parse(file_path) -> str
"""

import os
import json

# ============================================================
#  各格式解析器
# ============================================================

def _parse_txt(file_path: str) -> str:
    """解析纯文本文件，自动检测编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底：忽略错误
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _parse_md(file_path: str) -> str:
    """解析 Markdown 文件（本质上就是纯文本）"""
    return _parse_txt(file_path)


def _parse_docx(file_path: str) -> str:
    """解析 Word 文档（.docx）"""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("请安装 python-docx: pip install python-docx")

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    # 也提取表格内容
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(' | '.join(cells))
    return '\n'.join(paragraphs)


def _parse_pdf(file_path: str) -> str:
    """解析 PDF 文件"""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("请安装 pdfplumber: pip install pdfplumber")

    texts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texts.append(page_text)
    return '\n'.join(texts)


def _parse_pptx(file_path: str) -> str:
    """解析 PowerPoint 文件"""
    try:
        from pptx import Presentation
    except ImportError:
        raise ImportError("请安装 python-pptx: pip install python-pptx")

    prs = Presentation(file_path)
    texts = []
    for slide_num, slide in enumerate(prs.slides, 1):
        texts.append(f'[幻灯片 {slide_num}]')
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)
        # 也提取表格
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        texts.append(' | '.join(cells))
    return '\n'.join(texts)


def _parse_ipynb(file_path: str) -> str:
    """解析 Jupyter Notebook 文件"""
    try:
        import nbformat
    except ImportError:
        raise ImportError("请安装 nbformat: pip install nbformat")

    with open(file_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    texts = []
    for cell in nb.cells:
        source = cell.get('source', '')
        if isinstance(source, list):
            source = ''.join(source)
        source = source.strip()
        if not source:
            continue
        if cell.cell_type == 'markdown':
            texts.append(f'[Markdown] {source}')
        elif cell.cell_type == 'code':
            # 保留代码和输出
            texts.append(f'[Code]\n{source}')
            outputs = cell.get('outputs', [])
            for out in outputs:
                if out.get('output_type') == 'stream':
                    text_out = out.get('text', '')
                    if isinstance(text_out, list):
                        text_out = ''.join(text_out)
                    if text_out.strip():
                        texts.append(f'[Output] {text_out.strip()}')
                elif out.get('output_type') == 'execute_result':
                    data = out.get('data', {})
                    text_plain = data.get('text/plain', '')
                    if isinstance(text_plain, list):
                        text_plain = ''.join(text_plain)
                    if text_plain.strip():
                        texts.append(f'[Output] {text_plain.strip()}')
    return '\n\n'.join(texts)


def _parse_xlsx(file_path: str) -> str:
    """解析 Excel 文件"""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("请安装 openpyxl: pip install openpyxl")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    texts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        texts.append(f'[工作表: {sheet_name}]')
        rows_text = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                rows_text.append(' | '.join(cells))
        texts.append('\n'.join(rows_text))
    wb.close()
    return '\n\n'.join(texts)


# ============================================================
#  格式 → 解析器 映射
# ============================================================

PARSER_MAP = {
    '.txt': _parse_txt,
    '.md': _parse_md,
    '.docx': _parse_docx,
    '.pdf': _parse_pdf,
    '.pptx': _parse_pptx,
    '.ipynb': _parse_ipynb,
    '.xlsx': _parse_xlsx,
    '.xls': _parse_xlsx,
}

SUPPORTED_EXTENSIONS = list(PARSER_MAP.keys())


# ============================================================
#  统一入口
# ============================================================

def parse(file_path: str) -> str:
    """
    根据文件后缀自动选择解析器，返回纯文本内容。

    Args:
        file_path: 文件路径

    Returns:
        解析后的纯文本字符串

    Raises:
        ValueError: 不支持的文件格式
        FileNotFoundError: 文件不存在
        ImportError: 缺少对应解析库
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in PARSER_MAP:
        supported = ', '.join(SUPPORTED_EXTENSIONS)
        raise ValueError(f"不支持的文件格式 '{ext}'。支持: {supported}")

    parser = PARSER_MAP[ext]
    return parser(file_path)


# ============================================================
#  快速自测
# ============================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print(f"用法: python document_parser.py <文件路径>")
        print(f"支持格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)

    path = sys.argv[1]
    try:
        result = parse(path)
        print(f'=== 文件: {path} ===')
        print(f'=== 字符数: {len(result)} ===')
        print(result[:2000])
    except Exception as e:
        print(f'解析失败: {e}')
