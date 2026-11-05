"""
模型下载工具 - 从 ModelScope 下载 embedding 模型到本地
运行: python download_model.py

ModelScope 上的中文轻量模型：
  iic/nlp_corom_sentence-embedding_chinese-base  (约 400MB，中文专用)
"""

import os
import sys
import shutil

MODELSCOPE_MODEL = 'iic/nlp_corom_sentence-embedding_chinese-base'
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'embedding')


def download_from_modelscope():
    """从 ModelScope 下载模型到本地目录"""
    from modelscope import snapshot_download

    print(f'模型: {MODELSCOPE_MODEL}')
    print(f'本地路径: {LOCAL_MODEL_DIR}')

    if os.path.exists(LOCAL_MODEL_DIR) and os.listdir(LOCAL_MODEL_DIR):
        print('模型已存在，跳过下载')
        return LOCAL_MODEL_DIR

    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    print('开始下载...')
    snapshot_download(MODELSCOPE_MODEL, cache_dir=LOCAL_MODEL_DIR)
    print('下载完成！')
    return LOCAL_MODEL_DIR


if __name__ == '__main__':
    try:
        path = download_from_modelscope()
        print(f'\n模型路径: {path}')
        print('请在你的代码中使用此路径作为 model_name')
    except Exception as e:
        print(f'下载失败: {e}')
        print('\n请检查：1) 网络连接  2) 磁盘空间（约 400MB）')
        sys.exit(1)
