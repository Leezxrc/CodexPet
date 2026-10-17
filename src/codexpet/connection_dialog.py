import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from .client import Cancelled, UsageError
from .connection import ChatGPTLoginRequired, connect_account
from .i18n import Translator


class LocalizedText:
    """Retain the source text so an active connection can switch languages."""
    def __init__(self, text, translator):
        self.translator = translator
        self.source_text = text
        super().__init__(translator(text))

    def setText(self, text):
        self.source_text = text
        super().setText(self.translator(text))


class LocalizedLabel(LocalizedText, QLabel):
    pass


class LocalizedButton(LocalizedText, QPushButton):
    pass


class ConnectionWorker(QThread):
    progress = Signal(str)
    connected = Signal(str, object)
    failure = Signal(str, bool)

    def __init__(self, path, replace_login=False, parent=None):
        super().__init__(parent)
        self.path = path
        self.replace_login = replace_login
        self.cancel = threading.Event()

    def run(self):
        try:
            path, snapshot = connect_account(self.path, self.cancel, self.progress.emit, self.replace_login)
            if not self.cancel.is_set():
                self.connected.emit(path, snapshot)
        except Cancelled:
            self.failure.emit('连接已取消，可以随时重试。', False)
        except ChatGPTLoginRequired as exc:
            self.failure.emit(str(exc), True)
        except UsageError as exc:
            self.failure.emit(str(exc), False)
        except Exception:
            self.failure.emit('连接未完成，请重试或手动选择已安装的 codex.exe。', False)


class ConnectionDialog(QDialog):
    connected = Signal(str, object)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.translate = Translator(settings.get('language', 'zh-CN'))
        self.worker = None
        self.replace_login = False
        self.close_requested = False
        self.setWindowTitle(self.translate('连接 Codex · 码伴'))
        self.setFixedWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setStyleSheet('''QDialog { background:#262132; color:#eee9f6; }
            QLabel { color:#eee9f6; font:13px "Microsoft YaHei UI"; }
            QPushButton { background:#594775; color:#fff; border:0; border-radius:7px; padding:10px 18px; font:13px "Microsoft YaHei UI"; }
            QPushButton:disabled { background:#3a3347; color:#9f96ad; }
            QProgressBar { border:0; background:#3a3347; border-radius:3px; height:6px; }
            QProgressBar::chunk { background:#c1b1f4; }''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        title = LocalizedLabel('让码伴帮你看着额度', self.translate)
        title.setWordWrap(True)
        title.setStyleSheet('font-size:20px; font-weight:600;')
        layout.addWidget(title)
        description = LocalizedLabel('自动检测 Codex 并复用已有登录。\n缺少 CLI 时会下载 OpenAI 官方版本；未登录时打开浏览器授权。', self.translate)
        description.setWordWrap(True)
        layout.addWidget(description)
        self.status_label = LocalizedLabel('准备好后，点击下方按钮开始。', self.translate)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(64)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        note = LocalizedLabel('无需填写 API Key。密码和验证码只在官方登录页面输入。\n请与 Codex 桌面应用使用同一账号；重新登录会更新 CLI 登录。', self.translate)
        note.setStyleSheet('color:#aaa1bb;font-size:11px;')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        self.start_button = LocalizedButton('一键连接 Codex', self.translate)
        self.start_button.clicked.connect(self.start)
        self.cancel_button = LocalizedButton('关闭', self.translate)
        self.cancel_button.clicked.connect(self.reject)
        self.login_button = LocalizedButton('重新登录', self.translate)
        self.login_button.clicked.connect(self.relogin)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.login_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

    def retranslate(self, language):
        self.translate.language = language
        self.setWindowTitle(self.translate('连接 Codex · 码伴'))
        for widget in self.findChildren(QLabel) + self.findChildren(QPushButton):
            if isinstance(widget, LocalizedText):
                widget.setText(widget.source_text)
        self.adjustSize()

    def busy(self):
        return self.worker is not None

    def relogin(self):
        if not self.busy():
            self.replace_login = True
            self.start()

    def start(self):
        if self.busy():
            return
        self.close_requested = False
        self.start_button.setEnabled(False)
        self.login_button.setEnabled(False)
        self.cancel_button.setText('取消连接')
        self.progress_bar.show()
        self.worker = ConnectionWorker(str(self.settings.get('cli_path', '') or ''), self.replace_login, self)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.connected.connect(self.on_connected)
        self.worker.failure.connect(self.on_failure)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_connected(self, path, snapshot):
        if self.close_requested:
            return
        self.replace_login = False
        self.status_label.setText('连接成功！额度、重置卡和额外积分已同步。\n以后打开码伴会自动连接。')
        self.start_button.setText('重新检测')
        self.connected.emit(path, snapshot)

    def on_failure(self, message, needs_login):
        self.status_label.setText(message)
        self.replace_login = needs_login
        self.start_button.setText('使用 ChatGPT 登录' if needs_login else '重试连接')

    def on_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.progress_bar.hide()
        self.start_button.setEnabled(True)
        self.login_button.setEnabled(True)
        self.cancel_button.setText('关闭')
        if self.close_requested:
            super().reject()

    def reject(self):
        if self.busy():
            self.close_requested = True
            self.worker.cancel.set()
            self.status_label.setText('正在取消连接…')
            return
        super().reject()

    def closeEvent(self, event):
        if self.busy():
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)
