"""
登录窗口
风格与主界面保持一致：白/淡蓝/薄荷绿主色调
简单输入用户名即可登入（演示用，未做真实鉴权）
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from styles import get_login_stylesheet


class LoginWindow(QWidget):
    """登录窗口"""

    # 自定义信号：登录成功时携带用户名
    login_success = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录 - AI Engineer Mentor")
        self.setFixedSize(420, 460)
        self._init_ui()
        self.setStyleSheet(get_login_stylesheet())

    def _init_ui(self):
        # 根容器（背景色）
        root = QWidget(self)
        root.setObjectName("loginRoot")
        root.setGeometry(0, 0, self.width(), self.height())

        # 居中卡片
        card = QWidget(root)
        card.setObjectName("loginCard")
        card.setFixedSize(320, 360)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 30))
        card.setGraphicsEffect(shadow)

        # 用一个外层 layout 把 card 居中
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        outer.addWidget(card, alignment=Qt.AlignCenter)
        outer.addStretch()

        # 卡片内部布局
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(14)

        # 标题
        title = QLabel("AI Engineer Mentor")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("课程咨询助手")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(18)

        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setFixedHeight(44)
        self.username_input.returnPressed.connect(self._on_login)
        layout.addWidget(self.username_input)

        # 提示
        tip = QLabel("演示版：任意非空用户名即可登录")
        tip.setObjectName("loginSubtitle")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        # 登录按钮
        self.login_btn = QPushButton("登 录")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()

        # 监听输入框，控制按钮可点击
        self.username_input.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str):
        self.login_btn.setEnabled(bool(text.strip()))

    def _on_login(self):
        name = self.username_input.text().strip()
        if not name:
            return
        self.login_success.emit(name)
        self.close()
