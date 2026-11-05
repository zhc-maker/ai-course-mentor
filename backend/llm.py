"""
LLM 推理模块 - 基于 HuggingFace Transformers

使用本地已下载的 Qwen2.5-0.5B-Instruct（轻量、CPU 友好）
"""

import os

# 本地模型路径（可选，通过环境变量配置，避免硬编码本机路径）
# 例如: export LLM_MODEL_PATH=/path/to/Qwen2.5-0.5B-Instruct
LOCAL_MODEL_PATH = os.environ.get('LLM_MODEL_PATH', '')
# 备用模型名
FALLBACK_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'


class LLM:
    """本地 LLM 推理封装"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path or self._find_model_path()
        self._model = None
        self._tokenizer = None

    def _find_model_path(self) -> str:
        """按优先级查找可用模型"""
        # 1. 预设本地路径（若通过环境变量指定）
        if LOCAL_MODEL_PATH and os.path.isdir(LOCAL_MODEL_PATH) and os.path.isfile(os.path.join(LOCAL_MODEL_PATH, 'model.safetensors')):
            print(f'[LLM] 使用本地模型: {LOCAL_MODEL_PATH}')
            return LOCAL_MODEL_PATH

        # 2. HF 缓存中查找
        cache = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
        for d in os.listdir(cache) if os.path.isdir(cache) else []:
            if d.startswith('models--Qwen--Qwen2'):
                snap_dir = os.path.join(cache, d, 'snapshots')
                if os.path.isdir(snap_dir):
                    for snap in os.listdir(snap_dir):
                        full = os.path.join(snap_dir, snap)
                        if os.path.isfile(os.path.join(full, 'model.safetensors')):
                            print(f'[LLM] 找到缓存模型: {full}')
                            return full

        # 3. 回退到模型名（需要联网）
        print(f'[LLM] 未找到本地模型，回退到 {FALLBACK_MODEL}')
        return FALLBACK_MODEL

    def _ensure_loaded(self):
        """延迟加载模型"""
        if self._model is not None:
            return
        os.environ.setdefault('HF_HUB_OFFLINE', '1')  # 强制用本地
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print(f'[LLM] 加载模型: {self.model_path} ...')
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        self._model.eval()
        print('[LLM] 模型加载完成')

    def chat(self, prompt: str, max_new_tokens: int = 400, temperature: float = 0.5,
             system_message: str = None) -> str:
        """
        根据 prompt 生成回复。

        Args:
            prompt: 完整的 prompt 文本
            max_new_tokens: 最大生成 token 数
            temperature: 采样温度
            system_message: 可选的自定义 system message，覆盖默认

        Returns:
            生成的回复文本
        """
        self._ensure_loaded()
        import torch

        # 用 chat template 包装
        if system_message is None:
            system_message = '你是一个专业的课程咨询助手，名字叫 AI Engineer Mentor。回答要简洁、有条理。'
        messages = [
            {'role': 'system', 'content': system_message},
            {'role': 'user', 'content': prompt},
        ]
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )

        inputs = self._tokenizer(text, return_tensors='pt').to(self._model.device)
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        # 只取生成的部分
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        reply = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        return reply.strip()


if __name__ == '__main__':
    llm = LLM()
    print('--- 测试 ---')
    print(llm.chat('你好，请用一句话介绍你自己。'))
