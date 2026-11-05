# 基于 RAG 的课程智能咨询助手（AI Engineer Mentor）

一个**完全本地运行**的课程咨询助手：上传课程资料后，系统会先判断问题类型，再决定「查本地知识库 / 联网搜索 / 直接对话」，最后由本地小模型生成回答。

> 项目特点：**不依赖 LangChain 等编排框架**，RAG 链路（解析 → 分块 → 向量化 → 检索 → Prompt 组装）全部手写，便于逐环节调优与排查。

## 为什么做这个

课程咨询里存在大量重复问题（作业要求、课件下载、知识点解释），而通用大模型不了解内部课程资料，直接回答容易编造。本项目用「先检索、再生成」的方式把回答锚定在真实资料上；同时考虑到资料敏感性与硬件限制，整套系统可在纯 CPU 环境本地运行。

## 核心能力

| 能力 | 实现 |
|------|------|
| 多格式资料解析 | txt / docx / pdf / pptx / ipynb / xlsx / md 共 7 种，统一抽成纯文本并附来源文件名 |
| 知识库构建 | 段落优先 + 滑动窗口分块（500 字 / 50 字重叠）→ 中文句向量 → FAISS 索引落盘复用 |
| 三类意图路由 | `RAG`（课程问答）/ `WEB`（实时信息）/ `CHAT`（闲聊），低于阈值时由 LLM 二次判断兜底 |
| 联网搜索 | `WEB` 类问题调用 Tavily，结果注入 Prompt 并附来源链接 |
| 多轮对话 | 按 session 保存历史（最多 20 轮），注入最近 10 轮，支持「它多少钱」这类指代 |
| 复杂问题处理 | 复杂查询拆分为多轮子任务；位置类查询自动补充城市信息 |
| 追问建议 | 每轮回答后生成后续推荐问题 |
| 幻觉控制 | 检索相似度显式进 Prompt、Prompt 约束不许编造、检索为空走拒答模板 |

## 技术栈

- **后端**：Flask + Flask-CORS，REST API
- **向量检索**：FAISS（`IndexFlatIP`）+ SentenceTransformers 中文句向量
- **生成模型**：Qwen2.5-0.5B-Instruct（Transformers，本地 CPU 推理）
- **联网搜索**：Tavily API（可选，不配也能跑）
- **前端**：PyQt5 登录窗 + HTML/JS 聊天界面（`index.html`）

> 所有 API Key 都通过环境变量读取，仓库中不含任何密钥。

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. （可选）配置联网搜索

```bash
cp .env.example .env       # 填入 TAVILY_API_KEY
# 或直接在终端设置环境变量
export TAVILY_API_KEY=tvly-xxxxxxxx      # Windows PowerShell: $env:TAVILY_API_KEY="..."
```

不配置时 `WEB` 意图会返回提示信息，RAG 和闲聊功能不受影响。

### 3. 启动后端

```bash
python backend/server.py
# Flask 监听 http://127.0.0.1:5000
```

服务首次启动会自动扫描 `knowledge_base/` 并构建 FAISS 索引；也可以用 `python backend/rag_pipeline.py` 单独重建。

### 4. 启动前端（二选一）

```bash
# A. 桌面登录窗 + 自动打开浏览器
python main.py

# B. 直接打开网页（需自行起一个静态服务）
python -m http.server 8080
# 浏览器访问 http://127.0.0.1:8080/index.html
```

## 目录结构

```
ai-course-mentor/
├── backend/
│   ├── server.py             # Flask 服务：意图路由、会话历史、API
│   ├── rag_pipeline.py       # RAG 全流程编排
│   ├── document_parser.py    # 7 种格式解析器
│   ├── chunker.py            # 分块策略
│   ├── embedder.py           # 句向量（含 TF-IDF 降级方案）
│   ├── vector_store.py       # FAISS 索引增删查与持久化
│   ├── intent_classifier.py  # 原型向量意图分类
│   ├── web_searcher.py       # Tavily 封装
│   ├── llm.py                # 本地 Qwen 推理封装
│   └── download_model.py     # 模型下载辅助脚本
├── knowledge_base/           # 示例课程文档
├── uploads/                  # 用户上传文件（运行时生成）
├── vector_index/             # FAISS 索引（运行时生成）
├── docs/frontend-stage1.md   # 阶段一前端需求记录
├── index.html / main.py / *.py   # 前端界面
└── README.md
```

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 提问，返回 `reply` / `intent` / `confidence` / `sources` / `suggestions` |
| `/api/upload` | POST | 上传课程文件，解析后增量加入知识库 |
| `/api/kb/status` | GET | 查询当前知识库向量条数 |

请求示例：

```bash
curl -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"什么是 QLoRA？","session_id":"demo"}'
```

## 一次提问的处理流程

```
用户提问
  → 保存进 session 历史
  → 意图分类（原型问句质心相似度，低置信度交给 LLM 兜底）
  → 按意图路由
      ├─ RAG  : FAISS 取 top-3 → 拼装带相似度与「不许编造」约束的 Prompt
      ├─ WEB  : Tavily 搜索 → 结果注入 Prompt（附来源）
      └─ CHAT : 直接对话
  → 注入最近 10 轮历史 → 本地 Qwen 生成
  → 保存回复 + 生成追问建议 → 返回前端
```

## 设计取舍与已知边界

- **不用 LangChain**：链路短、模块少，手写实现可控且便于逐环节调试；代价是需要自己维护编排逻辑。
- **意图分类无训练数据**：采用「每类手写典型问句 → 向量化求质心 → 相似度匹配」的轻量方案，不依赖标注集；边界问题由 LLM 二次判断兜底。
- **生成模型较小**：0.5B 模型在 CPU 上可用，但复杂推理能力有限，因此强调「检索提供事实、模型只负责组织语言」。
- **会话保存在内存**：重启服务后历史丢失，适合本地演示；生产环境应换成 SQLite/Redis。
- **单机部署**：未做并发与鉴权设计，登录窗为演示用途。

## 数据与模型

仓库**不包含**模型权重与向量索引（体积大且可重新生成）：

- 生成模型：`Qwen/Qwen2.5-0.5B-Instruct`（首次使用自动从 HuggingFace / ModelScope 下载，也可设 `LLM_MODEL_PATH` 指向本地目录）
- 句向量模型：优先 `iic/nlp_corom_sentence-embedding_chinese-base`，缺失时降级到 `paraphrase-multilingual-MiniLM-L12-v2`，再降级到 TF-IDF
- 知识库：`knowledge_base/` 内附一篇示例文档，替换为自己的课程资料后重建索引即可

## License

MIT
