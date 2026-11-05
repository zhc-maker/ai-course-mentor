"""
主聊天窗口
构成：
  - 顶栏：深色背景，显示当前用户 + 登出按钮
  - 侧栏：新建对话按钮 + 按时间分组的 session 列表
  - 主聊天区：展示当前 session 的消息，空时显示欢迎语
  - 底部输入区：上传按钮 + 输入框（带 hint）+ 发送按钮
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFileDialog, QButtonGroup, QSizePolicy, QSpacerItem,
    QFrame, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from session_manager import SessionManager, Session


# 支持上传的文件类型（与截图中的 hint 文案保持一致）
SUPPORTED_FILE_TYPES = ("pdf", "docx", "txt", "pptx", "html", "ipynb")
HINT_TEXT = (
    "上传的文档不超过32M，支持的文件类型为："
    "'pdf'、'docx'、'txt'、'pptx'、'html'、'ipynb'，输入你的消息..."
)


class MainWindow(QWidget):
    """主聊天窗口"""

    # 自定义信号：登出
    logout_requested = pyqtSignal()

    def __init__(self, username: str):
        super().__init__()
        self.username = username
        self.session_manager = SessionManager()
        # 当前选中的 session 按钮（用于高亮）
        self.session_btn_group = QButtonGroup(self)
        self.session_btn_group.setExclusive(True)
        self.session_btn_group.buttonClicked.connect(self._on_session_clicked)

        # 暂存上传文件名
        self.pending_file_name = ""

        self._init_ui()
        # 默认创建一个新对话
        self._on_new_chat()

    # =========================================================
    # UI 构建
    # =========================================================
    def _init_ui(self):
        self.setWindowTitle("AI Engineer Mentor - 课程咨询助手")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        # 整体垂直布局：顶栏 + 内容区
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 顶栏 ----
        main_layout.addWidget(self._build_top_bar())

        # ---- 主体：侧栏 + 聊天区 ----
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_side_bar())
        body.addWidget(self._build_chat_area(), 1)

        # 把 body 包成一个 QWidget
        body_widget = QWidget()
        body_widget.setLayout(body)
        main_layout.addWidget(body_widget, 1)

        # ---- 底部输入栏 ----
        main_layout.addWidget(self._build_input_bar())

    # ----- 顶栏 -----
    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(44)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # 左侧：用户名前缀
        prefix = QLabel("欢迎，")
        prefix.setStyleSheet("color:white; font-size:14px;")
        layout.addWidget(prefix)

        user_label = QLabel(self.username)
        user_label.setObjectName("topBarUser")
        layout.addWidget(user_label)

        # 红色"退出"徽章
        badge = QLabel(" 退出")
        badge.setObjectName("topBarBadge")
        layout.addSpacing(6)
        layout.addWidget(badge)

        layout.addStretch(1)

        # 右侧：登出按钮
        logout_btn = QPushButton("登出")
        logout_btn.setObjectName("logoutBtn")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)

        return bar

    # ----- 侧栏 -----
    def _build_side_bar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("sideBar")
        side.setFixedWidth(220)

        layout = QVBoxLayout(side)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 新建对话按钮
        new_btn = QPushButton("+ 新建对话")
        new_btn.setObjectName("newChatBtn")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._on_new_chat)
        layout.addWidget(new_btn)

        # 滚动区域（用于放置 session 列表）
        self.session_scroll = QScrollArea()
        self.session_scroll.setWidgetResizable(True)
        self.session_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.session_container = QWidget()
        self.session_list_layout = QVBoxLayout(self.session_container)
        self.session_list_layout.setContentsMargins(0, 4, 0, 4)
        self.session_list_layout.setSpacing(6)
        self.session_list_layout.addStretch(1)

        self.session_scroll.setWidget(self.session_container)
        layout.addWidget(self.session_scroll, 1)

        return side

    # ----- 主聊天区 -----
    def _build_chat_area(self) -> QWidget:
        chat = QWidget()
        chat.setObjectName("chatArea")

        layout = QVBoxLayout(chat)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch(1)  # 把消息往上推

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, 1)

        return chat

    # ----- 底部输入栏 -----
    def _build_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("inputBar")
        bar.setFixedHeight(110)

        layout = QVBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 14)
        layout.setSpacing(6)

        # 第一行：hint 文本
        hint = QLabel(HINT_TEXT)
        hint.setObjectName("fileHintLabel")
        layout.addWidget(hint)

        # 第二行：上传 + 输入 + 发送
        row = QHBoxLayout()
        row.setSpacing(10)

        self.upload_btn = QPushButton("📎 上传")
        self.upload_btn.setObjectName("uploadBtn")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self._on_upload)
        row.addWidget(self.upload_btn)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText(HINT_TEXT)
        self.message_input.setFixedHeight(36)
        self.message_input.returnPressed.connect(self._on_send)
        self.message_input.textChanged.connect(self._on_input_changed)
        row.addWidget(self.message_input, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setEnabled(False)
        row.addWidget(self.send_btn)

        layout.addLayout(row)

        return bar

    # =========================================================
    # 侧栏刷新
    # =========================================================
    def _refresh_sidebar(self):
        """根据 session_manager 的数据重建侧栏"""
        # 清空旧 widget（保留 stretch）
        while self.session_list_layout.count() > 0:
            item = self.session_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        current_id = self.session_manager.current_session_id
        groups = self.session_manager.grouped_by_time()

        any_session = False
        for group_name in ["今天", "昨天", "前天", "更早"]:
            sessions = groups.get(group_name, [])
            if not sessions:
                continue
            any_session = True
            # 分组标题
            title = QLabel(group_name)
            title.setObjectName("groupTitle")
            self.session_list_layout.addWidget(title)

            for s in sessions:
                btn = QPushButton(f"● {s.preview()}")
                btn.setObjectName("sessionItem")
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setProperty("session_id", s.id)
                if s.id == current_id:
                    btn.setChecked(True)
                self.session_btn_group.addButton(btn)
                self.session_list_layout.addWidget(btn)

        if not any_session:
            empty = QLabel("暂无对话")
            empty.setStyleSheet("color:#9CA3AF; padding:12px; font-size:12px;")
            empty.setAlignment(Qt.AlignCenter)
            self.session_list_layout.addWidget(empty)

        self.session_list_layout.addStretch(1)

    # =========================================================
    # 聊天区刷新
    # =========================================================
    def _refresh_chat_area(self):
        """根据当前 session 的消息列表刷新聊天区"""
        # 清空（保留 stretch 在最后）
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        s = self.session_manager.get_current()

        if not s.messages:
            # 空白页：两个欢迎语
            self._add_welcome_messages()
        else:
            for msg in s.messages:
                self._append_message_widget(msg.role, msg.content, msg.file_name)

        # 把 stretch 加回末尾
        self.chat_layout.addStretch(1)
        # 滚动到底部
        QApplication.processEvents()
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _add_welcome_messages(self):
        """在主聊天区右上方显示两个欢迎语（按截图位置：右上方 + 居中靠上）"""
        # 用一个水平 layout 把欢迎标题推到右侧
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        welcome1 = QLabel("欢迎使用近屿智能课程咨询助手")
        welcome1.setObjectName("welcomeTitleDark")
        welcome1.setAlignment(Qt.AlignRight)
        row.addWidget(welcome1, 0, Qt.AlignRight)
        # 转成 widget
        wrap = QWidget()
        wrap.setLayout(row)
        self.chat_layout.addWidget(wrap, 0, Qt.AlignTop)

        # 第二行：左上方浅色欢迎语
        welcome2 = QLabel("同学你好！很高兴为你服务！")
        welcome2.setObjectName("welcomeTitleLight")
        self.chat_layout.addWidget(welcome2, 0, Qt.AlignLeft | Qt.AlignTop)

        # 占位 spacer，让两条欢迎语靠上
        self.chat_layout.addStretch(1)

    def _append_message_widget(self, role: str, content: str, file_name: str = ""):
        """追加一条消息气泡到聊天区（不重建已有 widget）"""
        text = content
        if file_name:
            text = f"📎 {file_name}\n{content}" if content else f"📎 {file_name}"

        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(560)
        if role == "user":
            label.setObjectName("messageUser")
        else:
            label.setObjectName("messageAI")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # 用 HBox 决定左右对齐
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(1)
            row.addWidget(label, 0, Qt.AlignRight)
        else:
            row.addWidget(label, 0, Qt.AlignLeft)
            row.addStretch(1)

        wrap = QWidget()
        wrap.setLayout(row)
        # 插入到 stretch 之前
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, wrap)

        # 滚到底
        QApplication.processEvents()
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    # =========================================================
    # 事件处理
    # =========================================================
    def _on_new_chat(self):
        self.session_manager.create_session()
        self._refresh_sidebar()
        self._refresh_chat_area()
        self.message_input.clear()
        self.message_input.setFocus()

    def _on_session_clicked(self, btn: QPushButton):
        session_id = btn.property("session_id")
        if not session_id:
            return
        self.session_manager.switch_session(session_id)
        self._refresh_chat_area()

    def _on_logout(self):
        ret = QMessageBox.question(
            self, "确认登出", f"确定要登出 {self.username} 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.logout_requested.emit()
            self.close()

    def _on_upload(self):
        """弹出文件选择对话框，校验类型，更新 hint + 暂存文件名"""
        filter_str = "支持的文件 (*.pdf *.docx *.txt *.pptx *.html *.ipynb)"
        path, _ = QFileDialog.getOpenFileName(self, "选择要上传的文件", "", filter_str)
        if not path:
            return
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        if ext not in SUPPORTED_FILE_TYPES:
            QMessageBox.warning(
                self, "文件类型不支持",
                f"暂不支持 .{ext} 格式。\n支持的格式：{', '.join(SUPPORTED_FILE_TYPES)}"
            )
            return
        self.pending_file_name = os.path.basename(path)
        QMessageBox.information(self, "上传成功", f"已选择文件：{self.pending_file_name}")

    def _on_input_changed(self, text: str):
        self.send_btn.setEnabled(bool(text.strip()) or bool(self.pending_file_name))

    def _on_send(self):
        text = self.message_input.text().strip()
        if not text and not self.pending_file_name:
            return

        # 1) 记录到 session
        self.session_manager.add_message("user", text, file_name=self.pending_file_name)

        # 2) 渲染用户消息
        self._append_message_widget("user", text, self.pending_file_name)

        # 3) 模拟 AI 回复
        ai_reply = self._mock_ai_reply(text, self.pending_file_name)
        self.session_manager.add_message("ai", ai_reply)
        self._append_message_widget("ai", ai_reply)

        # 4) 清空输入和暂存文件
        self.message_input.clear()
        self.pending_file_name = ""
        self.send_btn.setEnabled(False)

        # 5) 刷新侧栏（session 标题可能变化）
        self._refresh_sidebar()

    def _mock_ai_reply(self, text: str, file_name: str) -> str:
        """占位的 AI 回复逻辑，后续接后端时替换"""
        if file_name:
            return f"已收到你上传的文件「{file_name}」，正在解析中...\n（演示回复：真实场景会调用 RAG 流水线）"
        if not text:
            return "请告诉我你想咨询的问题～"
        return f"收到你的问题：{text}\n（演示回复：真实场景会调用大模型生成答案）"
