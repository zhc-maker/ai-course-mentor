"""
会话管理模块
负责管理多个 session（对话），每个 session 包含若干条消息
按"今天/昨天/前天/更早"对 session 进行时间分组
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Message:
    """单条消息"""
    role: str          # "user" 或 "ai"
    content: str       # 文本内容
    file_name: str = ""  # 附加文件名（可选）


@dataclass
class Session:
    """一个会话（一次对话）"""
    id: str                 # 唯一 id
    title: str              # 侧栏显示的标题（默认取首条用户消息）
    created_at: datetime    # 创建时间
    messages: List[Message] = field(default_factory=list)

    def preview(self) -> str:
        """侧栏显示的预览文本"""
        if not self.messages:
            return "新对话"
        # 显示最后一条用户消息或首条
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content[:18] + ("..." if len(msg.content) > 18 else "")
        return self.messages[-1].content[:18]


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions: List[Session] = []
        self.current_session_id: str = ""
        self._counter = 0

    def _gen_id(self) -> str:
        self._counter += 1
        return f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._counter}"

    def create_session(self) -> Session:
        """新建一个空 session，并切换为当前 session"""
        s = Session(
            id=self._gen_id(),
            title="新对话",
            created_at=datetime.now(),
        )
        self.sessions.insert(0, s)
        self.current_session_id = s.id
        return s

    def get_current(self) -> Session:
        if not self.sessions:
            return self.create_session()
        for s in self.sessions:
            if s.id == self.current_session_id:
                return s
        return self.sessions[0]

    def switch_session(self, session_id: str):
        self.current_session_id = session_id

    def add_message(self, role: str, content: str, file_name: str = ""):
        """向当前 session 追加一条消息"""
        s = self.get_current()
        s.messages.append(Message(role=role, content=content, file_name=file_name))
        # 自动用首条用户消息作为标题
        if role == "user" and (s.title == "新对话" or not s.title):
            s.title = content[:14] + ("..." if len(content) > 14 else "")

    def grouped_by_time(self) -> Dict[str, List[Session]]:
        """
        按时间分组：今天 / 昨天 / 前天 / 更早
        返回有序字典
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        day_before_start = today_start - timedelta(days=2)

        groups: Dict[str, List[Session]] = {
            "今天": [],
            "昨天": [],
            "前天": [],
            "更早": [],
        }

        for s in self.sessions:
            c = s.created_at
            if c >= today_start:
                groups["今天"].append(s)
            elif c >= yesterday_start:
                groups["昨天"].append(s)
            elif c >= day_before_start:
                groups["前天"].append(s)
            else:
                groups["更早"].append(s)
        return groups
