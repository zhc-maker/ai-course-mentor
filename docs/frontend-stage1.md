# AI Engineer Mentor - 阶段一前端

按题目要求实现的 PyQt5 桌面端前端界面，模拟"近屿智能课程咨询助手"。

## 功能一览

| 区域 | 组件 | 行为 |
|------|------|------|
| 登录窗口 | 用户名输入 + 登录按钮 | 输入任意非空用户名即可进入主界面（演示用，未做真实鉴权） |
| 顶栏 | 当前用户名 + 登出按钮 | 点击登出回到登录页 |
| 侧栏 | 新建对话按钮 + 历史 session 列表 | 新建一个 session 切换；列表按"今天 / 昨天 / 前天 / 更早"分组 |
| 主聊天区 | 消息列表 / 欢迎语 | 空白时显示两个欢迎语（位置与题目截图一致） |
| 底部输入 | 上传按钮 + 输入框 + 发送按钮 | 输入框无文本时显示 hint（支持的文件类型） |

## 文件结构

```
ai_mentor_ui/
├── main.py              # 程序入口，登录窗与主窗的切换控制器
├── login_window.py      # 登录窗口
├── main_window.py       # 主聊天窗口
├── session_manager.py   # 会话管理与时间分组
├── styles.py            # 全局 QSS 样式
├── requirements.txt     # 依赖
└── README.md
```

## 运行方式

```bash
# 1. 创建并激活虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python main.py
```

## 已实现的需求清单

- ✅ 界面由顶栏、侧栏、主聊天区构成
- ✅ 顶栏显示当前用户名，拥有登出按钮，点击登出回到登录界面
- ✅ 侧栏拥有新建对话按钮，点击新建 session
- ✅ 侧栏按"今天/昨天/前天/更早"对 session 简单时间分组
- ✅ 主聊天区无聊天记录时默认展示空白页，空白页显示两个欢迎语句
- ✅ 主聊天区下方是消息输入框，hint 文本提示支持的上传文件类型
- ✅ 输入框具有上传文件和发送消息按钮

## 后续可扩展

- 接 LLM 后端（替换 `_mock_ai_reply`），通过 HTTP/WebSocket 调用 Python 服务
- 接入 RAG：解析上传的 pdf/docx/ipynb 后做向量检索
- 会话持久化（SQLite/JSON 落盘到 `~/.ai_mentor/sessions.json`）
- 流式输出、Markdown 渲染、代码高亮
- 用户名与登录态真实鉴权
