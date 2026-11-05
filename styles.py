"""
全局样式表（QSS）
集中管理颜色、字体、组件样式，方便统一调整风格
"""

# 颜色常量（参考截图配色）
COLOR_BG_MAIN = "#FFFFFF"           # 主背景
COLOR_BG_SIDEBAR = "#FFFFFF"        # 侧栏背景
COLOR_BG_TOPBAR_DARK = "#3D4759"    # 顶栏深色
COLOR_BG_BUTTON_NEW = "#5EE2C0"     # 新建对话薄荷绿
COLOR_BG_BUTTON_SEND = "#2F9CFF"    # 发送按钮蓝
COLOR_BG_BUTTON_UPLOAD = "#5EE2C0"  # 上传按钮薄荷绿
COLOR_BG_GROUP_TITLE = "#E8F4FB"    # 侧栏分组标题背景
COLOR_BG_MESSAGE_SELF = "#E8F4FB"   # 自己的消息气泡
COLOR_BG_MESSAGE_AI = "#F5F7FA"     # AI 消息气泡
COLOR_BG_INPUT = "#FFFFFF"          # 输入框背景
COLOR_BG_LOGIN = "#F4F8FB"          # 登录页背景

COLOR_TEXT_PRIMARY = "#1F2937"      # 主文本
COLOR_TEXT_SECONDARY = "#6B7280"    # 次要文本
COLOR_TEXT_DOT = "#2F9CFF"          # 会话圆点
COLOR_TEXT_WELCOME_DARK = "#2C3E50"  # 深色欢迎语
COLOR_TEXT_WELCOME_LIGHT = "#9CA3AF"  # 浅色欢迎语

COLOR_BORDER = "#E5E7EB"
COLOR_BORDER_INPUT = "#D1D5DB"

FONT_FAMILY = "Microsoft YaHei, PingFang SC, Segoe UI, sans-serif"


def get_app_stylesheet() -> str:
    """获取整个应用的全局样式表"""
    return f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        color: {COLOR_TEXT_PRIMARY};
        background-color: {COLOR_BG_MAIN};
    }}

    /* ===== 顶栏 ===== */
    QWidget#topBar {{
        background-color: {COLOR_BG_TOPBAR_DARK};
        border: none;
    }}
    QLabel#topBarUser {{
        color: white;
        font-size: 14px;
        padding: 0 4px;
    }}
    QLabel#topBarBadge {{
        color: white;
        background-color: #FF4D4F;
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#logoutBtn {{
        background-color: #FF4D4F;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#logoutBtn:hover {{
        background-color: #FF7875;
    }}

    /* ===== 侧栏 ===== */
    QWidget#sideBar {{
        background-color: {COLOR_BG_SIDEBAR};
        border-right: 1px solid {COLOR_BORDER};
    }}
    QPushButton#newChatBtn {{
        background-color: {COLOR_BG_BUTTON_NEW};
        color: white;
        border: none;
        border-radius: 16px;
        padding: 8px 0;
        font-size: 14px;
        font-weight: bold;
    }}
    QPushButton#newChatBtn:hover {{
        background-color: #4ED1B0;
    }}
    QLabel#groupTitle {{
        background-color: {COLOR_BG_GROUP_TITLE};
        color: {COLOR_TEXT_PRIMARY};
        font-size: 13px;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 4px;
    }}
    QPushButton#sessionItem {{
        background-color: transparent;
        color: {COLOR_TEXT_PRIMARY};
        border: none;
        text-align: left;
        padding: 6px 8px;
        font-size: 13px;
    }}
    QPushButton#sessionItem:hover {{
        background-color: #F0F4F8;
        border-radius: 4px;
    }}
    QPushButton#sessionItem:checked {{
        background-color: #DCEEFB;
        border-radius: 4px;
    }}
    QLabel#sessionDot {{
        color: {COLOR_TEXT_DOT};
        font-size: 14px;
    }}

    /* ===== 主聊天区 ===== */
    QWidget#chatArea {{
        background-color: {COLOR_BG_MAIN};
    }}
    QLabel#welcomeTitleDark {{
        color: {COLOR_TEXT_WELCOME_DARK};
        font-size: 18px;
        font-weight: bold;
    }}
    QLabel#welcomeTitleLight {{
        color: {COLOR_TEXT_WELCOME_LIGHT};
        font-size: 14px;
    }}
    QLabel#messageUser {{
        background-color: {COLOR_BG_MESSAGE_SELF};
        color: {COLOR_TEXT_PRIMARY};
        padding: 10px 14px;
        border-radius: 10px;
        font-size: 14px;
    }}
    QLabel#messageAI {{
        background-color: {COLOR_BG_MESSAGE_AI};
        color: {COLOR_TEXT_PRIMARY};
        padding: 10px 14px;
        border-radius: 10px;
        font-size: 14px;
    }}

    /* ===== 底部输入区 ===== */
    QWidget#inputBar {{
        background-color: {COLOR_BG_MAIN};
        border-top: 1px solid {COLOR_BORDER};
    }}
    QPushButton#uploadBtn {{
        background-color: {COLOR_BG_BUTTON_UPLOAD};
        color: white;
        border: none;
        border-radius: 14px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#uploadBtn:hover {{
        background-color: #4ED1B0;
    }}
    QLineEdit#messageInput {{
        background-color: {COLOR_BG_INPUT};
        border: 1px solid {COLOR_BORDER_INPUT};
        border-radius: 18px;
        padding: 8px 16px;
        font-size: 13px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLineEdit#messageInput:focus {{
        border: 1px solid {COLOR_BG_BUTTON_SEND};
    }}
    QPushButton#sendBtn {{
        background-color: {COLOR_BG_BUTTON_SEND};
        color: white;
        border: none;
        border-radius: 14px;
        padding: 6px 18px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#sendBtn:hover {{
        background-color: #1E80E0;
    }}
    QPushButton#sendBtn:disabled {{
        background-color: #B0DCFF;
    }}
    QLabel#fileHintLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 11px;
        padding-left: 8px;
    }}

    /* ===== 滚动条 ===== */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: #D1D5DB;
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: #9CA3AF;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def get_login_stylesheet() -> str:
    """登录窗口样式"""
    return f"""
    QWidget#loginRoot {{
        background-color: {COLOR_BG_LOGIN};
    }}
    QWidget#loginCard {{
        background-color: white;
        border-radius: 12px;
        border: 1px solid {COLOR_BORDER};
    }}
    QLabel#loginTitle {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 24px;
        font-weight: bold;
    }}
    QLabel#loginSubtitle {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 13px;
    }}
    QLineEdit#loginInput {{
        background-color: white;
        border: 1px solid {COLOR_BORDER_INPUT};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
    }}
    QLineEdit#loginInput:focus {{
        border: 1px solid {COLOR_BG_BUTTON_SEND};
    }}
    QPushButton#loginBtn {{
        background-color: {COLOR_BG_BUTTON_SEND};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 0;
        font-size: 15px;
        font-weight: bold;
    }}
    QPushButton#loginBtn:hover {{
        background-color: #1E80E0;
    }}
    QPushButton#loginBtn:disabled {{
        background-color: #B0DCFF;
    }}
    """
