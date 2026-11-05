"""
AI Engineer Mentor - 阶段一前端界面
入口文件：启动 PyQt5 登录窗口，登录后自动打开浏览器显示主聊天界面
运行：python main.py
"""

import sys
import os
import webbrowser
import subprocess
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from styles import get_app_stylesheet
from login_window import LoginWindow


PORT = 8080
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
server_process = None


def ensure_http_server():
    """确保 HTTP 服务器在后台运行；已在运行则跳过"""
    global server_process
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('127.0.0.1', PORT))
        sock.close()
        # 端口已被占用，说明服务器已在运行
        return
    except ConnectionRefusedError:
        sock.close()

    # 启动 HTTP 服务器
    python_exe = os.path.join(SERVER_DIR, '.venv', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = sys.executable
    server_process = subprocess.Popen(
        [python_exe, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'],
        cwd=SERVER_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)  # 等服务器就绪


def open_browser(username: str):
    """用系统默认浏览器打开主聊天页面"""
    from urllib.parse import quote
    url = f'http://127.0.0.1:{PORT}/index.html?user={quote(username)}'
    webbrowser.open(url)


class AppController:
    """应用控制器：PyQt5 登录 → 浏览器主界面"""

    def __init__(self, app: QApplication):
        self.app = app
        self.login_window: LoginWindow | None = None

    def start(self):
        self._show_login()

    def _show_login(self):
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self._on_login_success)
        self.login_window.show()

    def _on_login_success(self, username: str):
        # 关闭登录窗
        if self.login_window is not None:
            self.login_window.close()
            self.login_window = None

        # 启动 HTTP 服务器 + 打开浏览器
        ensure_http_server()
        open_browser(username)

        # 退出 PyQt 应用
        self.app.quit()


def main():
    # 高 DPI 适配
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyleSheet(get_app_stylesheet())

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    controller = AppController(app)
    controller.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
