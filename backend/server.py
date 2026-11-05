"""
后端 Flask 服务 - 提供 REST API 给前端调用

端点:
  POST /api/chat          - 聊天（文本 + 可选文件）
  POST /api/upload        - 上传文件 + 解析 + 加入知识库
  GET  /api/kb/status     - 知识库状态

启动: python server.py
默认端口: 5000
"""

import os
import sys
import json
import urllib.request
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 确保 backend 目录在 path 中，方便 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_pipeline import RAGPipeline
from document_parser import SUPPORTED_EXTENSIONS

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# 上传文件保存目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 全局实例
rag: RAGPipeline | None = None
classifier = None  # intent_classifier.IntentClassifier
searcher = None    # web_searcher.WebSearcher
llm_instance = None  # llm.LLM

# 对话历史存储（阶段四新增）
# 格式: {session_id: [{"role": "user"/"assistant", "content": "..."}, ...]}
# 每个 session 最多保留 20 轮
_conversation_histories: dict = {}
MAX_HISTORY_ROUNDS = 10  # 注入 prompt 的最近轮数


def get_history(session_id: str) -> list:
    """获取会话历史"""
    return _conversation_histories.get(session_id, [])


def add_to_history(session_id: str, role: str, content: str):
    """追加一条消息到历史，自动裁剪"""
    if session_id not in _conversation_histories:
        _conversation_histories[session_id] = []
    history = _conversation_histories[session_id]
    history.append({"role": role, "content": content})
    # 保留最近 40 条（20 轮）
    if len(history) > 40:
        _conversation_histories[session_id] = history[-40:]


def format_history_for_prompt(session_id: str, max_rounds: int = MAX_HISTORY_ROUNDS) -> str:
    """将对话历史格式化为 prompt 文本"""
    history = get_history(session_id)
    if not history:
        return ""
    # 取最近 N 轮
    recent = history[-(max_rounds * 2):]
    lines = []
    for msg in recent:
        role_label = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"]
        # 截断过长的消息
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)


def get_rag() -> RAGPipeline:
    """懒加载 RAG 管道"""
    global rag
    if rag is None:
        rag = RAGPipeline()
        # 尝试加载已有索引，没有则构建
        rag._ensure_initialized()
        if rag.vector_store.size == 0:
            print('[Server] 知识库为空，自动构建中 ...')
            rag.build_knowledge_base()
        else:
            print(f'[Server] 知识库已加载: {rag.vector_store.size} 条')
    return rag


def get_classifier():
    """懒加载意图分类器"""
    global classifier
    if classifier is None:
        from intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        classifier.fit()
        print('[Server] 意图分类器就绪')
    return classifier


def get_searcher():
    """懒加载网络搜索器"""
    global searcher
    if searcher is None:
        from web_searcher import WebSearcher
        searcher = WebSearcher()
        if searcher.api_key:
            print('[Server] 网络搜索器就绪')
        else:
            print('[Server] 网络搜索器: 未配置 API Key')
    return searcher


def get_llm():
    """懒加载 LLM"""
    global llm_instance
    if llm_instance is None:
        from llm import LLM
        print('[Server] 加载 LLM 模型 ...')
        llm_instance = LLM()
    return llm_instance


# ============================================================
#  API 端点
# ============================================================

@app.route('/api/kb/status', methods=['GET'])
def kb_status():
    """知识库状态"""
    r = get_rag()
    return jsonify({
        'success': True,
        'vector_count': r.vector_store.size,
        'vector_dim': r.embedder.dim,
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件，解析内容，加入知识库"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)

    # 检查后缀
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({
            'success': False,
            'error': f'不支持的文件格式 {ext}，支持: {", ".join(SUPPORTED_EXTENSIONS)}'
        }), 400

    file.save(save_path)
    print(f'[Server] 文件已保存: {save_path}')

    # 解析文件
    from document_parser import parse
    text = parse(save_path)
    char_count = len(text)

    # 加入知识库
    from chunker import chunk_text
    r = get_rag()
    chunks = chunk_text(text)
    for i in range(len(chunks)):
        chunks[i] = f'[来源: {filename}]\n\n{chunks[i]}'

    vectors = r.embedder.encode(chunks)
    r.vector_store.add(vectors, chunks)
    r.vector_store.save()

    return jsonify({
        'success': True,
        'filename': filename,
        'char_count': char_count,
        'chunks': len(chunks),
        'total_vectors': r.vector_store.size,
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口 - 阶段四：含对话历史 + 意图识别 → 路由"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体为空'}), 400

    message = data.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'error': '消息为空'}), 400

    session_id = data.get('session_id', 'default')

    # 保存用户消息到历史
    add_to_history(session_id, 'user', message)

    # 1. 意图识别（阶段三）
    clf = get_classifier()
    intent, confidence, intent_details = clf.classify(message)
    print(f'[Server] 意图: {intent} (置信度: {confidence:.3f}, 方法: {intent_details["method"]})')

    # 2. 获取对话历史上下文（阶段四新增）
    history_context = format_history_for_prompt(session_id)

    # 3. 阶段四模块 2：复杂查询拆分为多轮子任务
    try:
        if intent == 'rag' and is_complex_query(message):
            reply, sources = _handle_complex_rag(message, history_context)
        elif intent == 'web' and is_complex_query(message):
            reply, sources = _handle_complex_web(message, history_context)
        elif intent == 'rag':
            reply, sources = _handle_rag(message, history_context)
        elif intent == 'web':
            reply, sources = _handle_web(message, history_context)
        else:
            reply, sources = _handle_chat(message, history_context)
    except Exception as e:
        print(f'[Server] 处理失败: {e}，降级为通用对话')
        reply, sources = _handle_chat(message, history_context)

    # 保存 AI 回复到历史
    add_to_history(session_id, 'assistant', reply)

    # 4. 生成后续推荐问题（阶段四模块 3）
    suggest = []
    try:
        suggest = _suggest_questions(message, reply, intent)
    except Exception:
        pass

    return jsonify({
        'success': True,
        'reply': reply,
        'has_context': len(sources) > 0,
        'sources': sources,
        'intent': intent,
        'confidence': round(confidence, 3),
        'suggestions': suggest,
    })


def _build_prompt_with_history(base_prompt: str, history: str) -> str:
    """将对话历史注入 prompt"""
    if not history:
        return base_prompt
    return (
        f'【对话历史】\n{history}\n\n'
        f'---\n\n'
        f'{base_prompt}\n\n'
        f'请结合对话历史上下文回答用户问题。'
    )


def _handle_rag(message: str, history: str = '') -> tuple:
    """RAG 检索 → LLM 生成"""
    r = get_rag()
    if r.vector_store.size == 0:
        return ('当前知识库为空，你可以上传课程文件（PDF、Word、TXT 等），我就可以根据文件内容为你解答。', [])

    result = r.query(message)
    prompt = _build_prompt_with_history(result['prompt'], history)
    sources = [{'text': t[:200], 'score': round(s, 3)} for t, s in result['results']]

    system_msg = (
        '你是一个专业的中文助理，名字叫 AI Engineer Mentor。\n'
        '请基于用户提供的参考资料和对话历史，用简体中文回答。\n'
        '要求：答案要简洁有条理；资料不足时如实说明。'
    )
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=400, temperature=0.4, system_message=system_msg)
    return (reply, sources)


def _handle_web(message: str, history: str = '') -> tuple:
    """网络搜索 → LLM 生成"""
    sr = get_searcher()
    if not sr.api_key:
        return ('抱歉，网络搜索功能暂未配置 API Key。\n'
                '请设置环境变量 TAVILY_API_KEY 后重启服务。\n'
                '注册地址: https://tavily.com', [])

    search_query = maybe_enhance_query(message)
    print(f'[Server] 网络搜索: {search_query}')

    try:
        web_context = sr.search_for_prompt(search_query, max_results=3)
    except Exception as e:
        print(f'[Server] Tavily 搜索异常: {e}')
        web_context = ''

    if not web_context:
        print('[Server] 网络搜索无结果，让 LLM 直答')
        system_msg = '你是 AI Engineer Mentor，用简体中文回答用户问题。如果不知道答案请如实告知。'
        llm = get_llm()
        prompt = _build_prompt_with_history(
            f'用户问题: {message}\n请尝试回答（如果涉及实时信息就说不准）：',
            history
        )
        reply = llm.chat(prompt, max_new_tokens=300, temperature=0.5, system_message=system_msg)
        return (reply, [])

    sources = []
    try:
        sources = [{'text': r['title'], 'score': 1.0, 'url': r['url']}
                   for r in sr.search(search_query, max_results=3)]
    except Exception:
        pass

    base_prompt = (
        f'【参考资料】\n{web_context}\n\n'
        f'---\n'
        f'【用户问题】{message}\n\n'
        f'【回答要求】\n'
        f'1. 必须用简体中文回答\n'
        f'2. 资料是英文的，请先翻译关键信息再回答\n'
        f'3. 回答简洁有条理，末尾用 [来源] 注明出处\n'
        f'4. 不要直接复述英文原文'
    )
    prompt = _build_prompt_with_history(base_prompt, history)
    system_msg = '你是 AI Engineer Mentor，一个用简体中文回答问题的助手。'
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=400, temperature=0.3, system_message=system_msg)
    return (reply, sources)


def _handle_chat(message: str, history: str = '') -> tuple:
    """通用对话 → 直接 LLM"""
    base_prompt = f'用户: {message}\n\n请基于对话历史自然回复。'
    prompt = _build_prompt_with_history(base_prompt, history)
    system_msg = '你是 AI Engineer Mentor，一个自然的对话助理。要求：用简体中文，保持对话连贯性。'
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=200, temperature=0.7, system_message=system_msg)
    return (reply, [])


# ============================================================
#  阶段四模块 2：多轮任务路由
# ============================================================

def is_complex_query(message: str) -> bool:
    """判断是否为需要拆分的复杂任务"""
    # 简单启发式 + LLM 判断
    complex_keywords = ['先', '然后', '再', '接着', '最后', '同时', '并且',
                        '帮我查一下', '帮我找', '帮我总结', '整理', '分析']
    has_complex_kw = any(kw in message for kw in complex_keywords)
    # 长句子也更可能是复杂任务
    return has_complex_kw or len(message) > 50


def decompose_task(message: str) -> list:
    """将复杂任务拆分为子任务列表"""
    try:
        llm = get_llm()
        prompt = (
            '请将以下用户请求拆分为 2~5 个简单的子任务，每行一个，不要编号。\n\n'
            f'用户请求: {message}\n\n'
            '子任务列表:'
        )
        reply = llm.chat(prompt, max_new_tokens=100, temperature=0.3, system_message='拆分任务，每行输出一个子任务。')
        subtasks = [s.strip().lstrip('0123456789、.．-— ') for s in reply.split('\n') if s.strip()]
        if not subtasks:
            subtasks = [message]
        return subtasks
    except Exception:
        return [message]


# ============================================================
#  阶段四模块 3：后续问题推荐
# ============================================================

def _suggest_questions(message: str, reply: str, intent: str) -> list:
    """根据当前对话生成推荐问题"""
    try:
        llm = get_llm()
        prompt = (
            f'用户问: {message}\n'
            f'AI 答: {reply[:300]}\n\n'
            '请推荐 3 个用户可能接着问的问题，每行一个，不要编号。问题要自然简短。'
        )
        result = llm.chat(prompt, max_new_tokens=80, temperature=0.7,
                          system_message='生成后续问题，每行一个，不要编号。')
        questions = [s.strip().lstrip('0123456789、.．-— ') for s in result.split('\n') if s.strip()]
        return questions[:3]
    except Exception:
        return []


# ============================================================
#  阶段四模块 2：复杂任务执行器
# ============================================================

def _handle_complex_rag(message: str, history: str) -> tuple:
    """复杂 RAG 任务：拆分子任务，依次执行，合并结果"""
    subtasks = decompose_task(message)
    print(f'[Server] 复杂 RAG 拆分为 {len(subtasks)} 个子任务: {subtasks}')

    results_parts = []
    all_sources = []

    for task in subtasks:
        try:
            result = get_rag().query(task)
            results_parts.append(f'【子任务】{task}\n{result["prompt"]}')
            all_sources.extend(
                [{'text': t[:120], 'score': round(s, 3)} for t, s in result['results']]
            )
        except Exception as e:
            results_parts.append(f'【子任务】{task}\n(执行失败: {e})')

    combined = '\n\n'.join(results_parts)
    final_prompt = (
        f'【多轮检索结果】\n{combined}\n\n'
        f'---\n用户原始问题: {message}\n请综合以上所有检索结果，给出完整回答。'
    )
    prompt = _build_prompt_with_history(final_prompt, history)
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=600, temperature=0.4,
                     system_message='你是 AI Engineer Mentor。基于多轮检索结果综合回答，用简体中文。')
    return (reply, all_sources[:5])


def _handle_complex_web(message: str, history: str) -> tuple:
    """复杂网络搜索任务：拆分子任务，依次搜索，合并结果"""
    subtasks = decompose_task(message)
    print(f'[Server] 复杂 Web 拆分为 {len(subtasks)} 个子任务: {subtasks}')

    sr = get_searcher()
    parts = []
    all_sources = []

    for task in subtasks:
        try:
            ctx = sr.search_for_prompt(task, max_results=2)
            if ctx:
                parts.append(f'【子任务】{task}\n{ctx}')
            sources_raw = sr.search(task, max_results=2)
            all_sources.extend(
                [{'text': s.get('title', ''), 'score': 1.0, 'url': s.get('url', '')}
                 for s in sources_raw if s.get('title')]
            )
        except Exception:
            pass

    if not parts:
        return _handle_web(message, history)

    combined = '\n\n'.join(parts)
    final_prompt = (
        f'【多轮搜索结果】\n{combined}\n\n'
        f'---\n用户问题: {message}\n请综合结果用中文回答。'
    )
    prompt = _build_prompt_with_history(final_prompt, history)
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=600, temperature=0.3,
                     system_message='综合多轮搜索结果用中文回答。')
    return (reply, all_sources[:5])


# ============================================================

_location_cache = None  # IP 定位缓存，避免每次请求都调 API


def get_ip_location() -> str:
    """通过 IP 获取城市名（免费 API ip-api.com）"""
    global _location_cache
    if _location_cache is not None:
        return _location_cache
    try:
        url = 'http://ip-api.com/json/?lang=zh-CN&fields=city,country'
        req = urllib.request.Request(url, headers={'User-Agent': 'AI-Mentor/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            city = data.get('city', '')
            country = data.get('country', '')
            if city:
                _location_cache = f'{city}' if country == 'China' else f'{city},{country}'
                print(f'[Server] IP 定位: {_location_cache}')
                return _location_cache
    except Exception as e:
        print(f'[Server] IP 定位失败: {e}')
    return ''


LOCATION_KEYWORDS = ['天气', 'weather', '气温', '温度', '附近', '周边', '本地', '本地化',
                     '当地', '房价', '油价', '限行', '停电', '公交', '地铁']


def maybe_enhance_query(message: str) -> str:
    """如果消息含位置敏感词，自动附加城市名"""
    for kw in LOCATION_KEYWORDS:
        if kw in message.lower():
            city = get_ip_location()
            if city and city not in message:
                enhanced = f'{message} {city}'
                print(f'[Server] 查询增强: "{message}" → "{enhanced}"')
                return enhanced
            break
    return message


def _handle_web(message: str, history: str = '') -> tuple:
    """网络搜索 → LLM 生成（history 与上层调用签名保持一致）"""
    sr = get_searcher()
    if not sr.api_key:
        return ('抱歉，网络搜索功能暂未配置 API Key。\n'
                '请设置环境变量 TAVILY_API_KEY 后重启服务。\n'
                '注册地址: https://tavily.com', [])

    # 位置敏感查询自动附加城市
    search_query = maybe_enhance_query(message)
    print(f'[Server] 网络搜索: {search_query}')

    try:
        web_context = sr.search_for_prompt(search_query, max_results=3)
    except Exception as e:
        print(f'[Server] Tavily 搜索异常: {e}')
        web_context = ''

    if not web_context:
        # 搜索无结果/失败 - 直接让 LLM 基于通用知识回答
        print('[Server] 网络搜索无结果，让 LLM 直答')
        system_msg = '你是 AI Engineer Mentor，用简体中文回答用户问题。如果不知道答案请如实告知。'
        llm = get_llm()
        reply = llm.chat(
            f'用户问题: {message}\n请尝试回答（如果涉及实时信息就说不准）：',
            max_new_tokens=300, temperature=0.5, system_message=system_msg
        )
        return (reply, [])

    try:
        sources = [{'text': r['title'], 'score': 1.0, 'url': r['url']}
                   for r in sr.search(search_query, max_results=3)]
    except Exception:
        sources = []

    # 在 user prompt 里强制中文输出
    prompt = (
        f'【参考资料】\n{web_context}\n\n'
        f'---\n'
        f'【用户问题】{message}\n\n'
        f'【回答要求】\n'
        f'1. 必须用简体中文回答\n'
        f'2. 资料是英文的，请先翻译关键信息再回答\n'
        f'3. 回答简洁有条理，末尾用 [来源] 注明出处\n'
        f'4. 不要直接复述英文原文'
    )
    system_msg = '你是 AI Engineer Mentor，一个用简体中文回答问题的助手。'
    llm = get_llm()
    reply = llm.chat(prompt, max_new_tokens=400, temperature=0.3, system_message=system_msg)
    return (reply, sources)


def _handle_chat(message: str, history: str = '') -> tuple:
    """通用对话 → 直接 LLM（history 与上层调用签名保持一致）"""
    system_msg = (
        '你是一个专业的中文助理 AI Engineer Mentor，专长是回答用户问题。\n'
        '要求：用简体中文回答，简洁、友善、有条理。'
    )
    llm = get_llm()
    reply = llm.chat(message, max_new_tokens=200, temperature=0.7, system_message=system_msg)
    return (reply, [])


# ============================================================
#  启动
# ============================================================

if __name__ == '__main__':
    print('=' * 50)
    print('AI Engineer Mentor - 后端服务')
    print('=' * 50)
    print(f'上传目录: {UPLOAD_DIR}')
    print(f'API 地址: http://127.0.0.1:5000')
    print('=' * 50)
    app.run(host='127.0.0.1', port=5000, debug=False)
