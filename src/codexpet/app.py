from datetime import datetime
import argparse
import json
import math
from pathlib import Path
import sys
import threading
import time

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, QThread, Signal, QLockFile
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon, QWidget
from PySide6.QtCore import QUrl

from .client import Cancelled, UsageError, fetch_usage
from .quota import Snapshot, Window, reset_date, reset_text
from .settings import Settings, data_dir, project_root
from .appearance import APPEARANCES, PAT_DURATION, pat_transform

BASE_WIDTH = 300
TOP_MARGIN = 32
COMPACT_HEIGHT = 368
EXPANDED_HEIGHT = 520
CARD_TOP = 202
PURPLE = '#c1b1f4'
TEXT = '#f1edf9'
MUTED = '#a59fb8'


def asset_path(name):
    base = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else project_root()
    return base / 'assets' / name


class RefreshWorker(QThread):
    success = Signal(object)
    failure = Signal(str)

    def __init__(self, cli_path, parent=None):
        super().__init__(parent)
        self.cli_path = cli_path
        self.cancel = threading.Event()

    def run(self):
        try:
            result = fetch_usage(self.cli_path, self.cancel)
            if not self.cancel.is_set():
                self.success.emit(result)
        except Cancelled:
            pass
        except UsageError as exc:
            self.failure.emit(str(exc))
        except Exception:
            self.failure.emit('读取遇到异常，请检查 CLI 后刷新重试')


class PetWindow(QWidget):
    def __init__(self, settings=None, online=True, demo=False, tray=True):
        super().__init__()
        self.settings = settings or Settings()
        self.online = online
        self.demo = demo
        self.snapshot = None
        self.error = ''
        self.worker = None
        self.closing = False
        self.expanded = False
        self.scale = self.settings.get('scale', 1.0)
        if self.scale not in (0.8, 1.0, 1.25, 1.5):
            self.scale = 1.0
        self.on_top = bool(self.settings.get('on_top', True))
        self.motion = bool(self.settings.get('motion', True))
        self.bubble = ''
        self.bubble_until = 0
        self._press = None
        self._origin = None
        self._dragged = False
        self._hover = QPointF(-1, -1)
        self._tap_count = 0
        self.pat_started = -100.0
        self._sprite_cache = None
        self._sprite_key = None
        self._reset_attempt = None
        selected = self.settings.get('appearance', 'dragon')
        self.appearance = selected if isinstance(selected, str) and selected in APPEARANCES else 'dragon'
        self.pet = QPixmap(str(asset_path(APPEARANCES[self.appearance].asset)))
        if self.pet.isNull():
            raise RuntimeError('Missing pet appearance asset')
        self.setWindowTitle('CodexPet · 码伴')
        self.setWindowIcon(QIcon(self.pet))
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.resize_for_state()
        self.restore_position()
        self.tray = None
        if tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(QIcon(self.pet), self)
            self.tray.setToolTip('CodexPet · 码伴')
            self.tray.setContextMenu(self.make_menu())
            self.tray.activated.connect(self.tray_activate)
            self.tray.show()
        self.animation = QTimer(self)
        self.animation.setInterval(70)
        self.animation.timeout.connect(self.update)
        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self.tick)
        self.clock.start()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(120_000)
        self.refresh_timer.timeout.connect(self.refresh)
        if online:
            self.refresh_timer.start()
            QTimer.singleShot(200, self.refresh)
        if demo:
            now = time.time()
            self.snapshot = Snapshot(Window(34, 300, now + 7260), Window(5, 10080, now + 365400), 'Plus', now)

    def resize_for_state(self):
        self.setFixedSize(round(BASE_WIDTH * self.scale), round(((EXPANDED_HEIGHT if self.expanded else COMPACT_HEIGHT) + TOP_MARGIN) * self.scale))

    def restore_position(self):
        x, y = self.settings.get('x'), self.settings.get('y')
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)
            self.clamp_position()
        else:
            self.reset_position()

    def reset_position(self):
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 30, area.bottom() - self.height() - 24)
        self.clamp_position()

    def clamp_position(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right() - self.width() + 1)),
                  max(area.top(), min(self.y(), area.bottom() - self.height() + 1)))

    def save_position(self):
        self.settings.update(x=self.x(), y=self.y())

    def refreshing(self):
        return self.worker is not None and self.worker.isRunning()

    def refresh(self):
        if not self.online or self.refreshing() or self.closing:
            return
        self.worker = RefreshWorker(str(self.settings.get('cli_path', '') or ''), self)
        self.worker.success.connect(self.on_success)
        self.worker.failure.connect(self.on_failure)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()
        self.update()

    def worker_finished(self):
        worker = self.sender()
        if self.worker is worker:
            self.worker = None
        worker.deleteLater()
        self.update()

    def on_success(self, snapshot):
        self.snapshot = snapshot
        self.error = ''
        if self.tray:
            rows = []
            for window in (snapshot.primary, snapshot.secondary):
                if window and window.remaining is not None:
                    rows.append(f'{window.label}：剩余 {window.remaining:g}%')
            self.tray.setToolTip('CodexPet · 码伴\n' + '\n'.join(rows))
        self.update()

    def on_failure(self, message):
        self.error = message
        if self.tray:
            self.tray.setToolTip('CodexPet · 码伴\n暂未同步；点击查看详情')
        self.update()

    def tick(self):
        if self.bubble and time.monotonic() >= self.bubble_until:
            self.bubble = ''
        if not self.motion and time.monotonic() - self.pat_started > PAT_DURATION:
            self.animation.stop()
        if self.snapshot:
            due = tuple(w.resets_at for w in (self.snapshot.primary, self.snapshot.secondary) if w and w.reset_due())
            if due and due != self._reset_attempt and not self.refreshing():
                self._reset_attempt = due
                self.refresh()
        self.update()

    def show_bubble(self, message):
        self.bubble = message
        self.bubble_until = time.monotonic() + 3
        self.update()

    def pat_head(self):
        messages = ('嗯…再摸一下也可以。', '摸摸头，今天也辛苦啦。', '我会帮你看着额度的。', '收到你的摸摸啦 ♡')
        self.show_bubble(messages[self._tap_count % len(messages)])
        self._tap_count += 1
        self.pat_started = time.monotonic()
        # The optional idle animation switch does not disable deliberate feedback.
        self.animation.start()

    def stale(self):
        return bool(self.snapshot and (self.error or self.snapshot.stale()))

    def status(self):
        if self.demo:
            return '演示数据', PURPLE
        if self.refreshing():
            return '读取中', PURPLE
        if self.error:
            return ('旧数据' if self.snapshot else '未连接'), '#e9bd81'
        if self.stale():
            return '待刷新', '#e9bd81'
        return ('已同步', '#a9d6c6') if self.snapshot else ('等待连接', MUTED)

    @staticmethod
    def text(painter, x, y, width, height, value, size=12, color=TEXT, bold=False, align=None):
        font = QFont('Microsoft YaHei UI')
        font.setPixelSize(size)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.NoSubpixelAntialias)
        font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(x, y, width, height), align or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(self.scale, self.scale)
        p.translate(0, TOP_MARGIN)
        h = EXPANDED_HEIGHT if self.expanded else COMPACT_HEIGHT
        # Deliberately compact and fully transparent outside the pet and card.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 28))
        p.drawRoundedRect(QRectF(14, CARD_TOP + 4, 274, h - CARD_TOP - 14), 21, 21)
        p.setPen(QPen(QColor('#4a415e'), 1))
        p.setBrush(QColor(35, 31, 47, 248))
        p.drawRoundedRect(QRectF(12, CARD_TOP, 276, h - CARD_TOP - 16), 20, 20)
        pat_age = time.monotonic() - self.pat_started
        pat_active = 0 <= pat_age < PAT_DURATION
        bob = math.sin(time.monotonic() * 1.7) * 1.8 if self.motion and not self._dragged and not pat_active else 0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(30, 22, 45, 35))
        p.drawEllipse(QRectF(83, 190, 134, 13))
        key = (self.appearance, self.scale, self.devicePixelRatioF())
        if self._sprite_key != key:
            self._sprite_cache = self.pet.scaledToHeight(round(202 * self.scale * self.devicePixelRatioF()), Qt.TransformationMode.SmoothTransformation)
            self._sprite_key = key
        sprite_width = 202 * self.pet.width() / self.pet.height()
        p.save()
        if pat_active:
            vertical, angle = pat_transform(self.appearance, pat_age)
            p.translate(0, vertical)
            p.translate(150, 195)
            p.rotate(angle)
            p.translate(-150, -195)
        p.drawPixmap(QRectF((BASE_WIDTH - sprite_width) / 2, 1 + bob, sprite_width, 202), self._sprite_cache, QRectF(self._sprite_cache.rect()))
        p.restore()
        if pat_active:
            for x, y, delay in ((85, 80, 0), (208, 57, 0.15), (220, 104, 0.3)):
                age = max(0, pat_age - delay)
                p.save()
                p.translate(x, y - age * 21)
                p.setOpacity(max(0, 1 - age / 1.4))
                heart = QPainterPath(QPointF(0, 3))
                heart.cubicTo(-10, -5, -7, -12, 0, -6)
                heart.cubicTo(7, -12, 10, -5, 0, 3)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor('#e2acd9'))
                p.drawPath(heart)
                p.restore()
        self.text(p, 28, 213, 43, 23, '码伴', 15, TEXT, True)
        self.text(p, 74, 215, 65, 20, 'CODEXPET', 9, MUTED)
        status, status_color = self.status()
        p.setBrush(QColor(status_color))
        p.drawEllipse(QRectF(155, 223, 5, 5))
        self.text(p, 165, 215, 58, 20, status, 10, status_color)
        for rect in (QRectF(230, 211, 25, 27), QRectF(258, 211, 23, 27)):
            if rect.contains(self._hover):
                p.setBrush(QColor('#4a405d'))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 7, 7)
        self.text(p, 230, 211, 25, 27, '↻', 21, PURPLE, align=Qt.AlignmentFlag.AlignCenter)
        self.text(p, 258, 210, 23, 27, '⋯', 21, MUTED, align=Qt.AlignmentFlag.AlignCenter)
        for index, y in enumerate((245, 289)):
            window = (self.snapshot.primary, self.snapshot.secondary)[index] if self.snapshot else None
            label = window.label if window else ('主要额度' if index == 0 else '次要额度')
            remaining = window.remaining if window else None
            expired = window is not None and window.reset_due()
            value = '—' if remaining is None else f'{remaining:g}%'
            color = '#a9d6c6' if index else PURPLE
            if remaining is not None and remaining < 20:
                color = '#ecb481'
            if self.stale():
                color = '#b6a899'
            self.text(p, 29, y, 130, 21, label, 12, MUTED)
            self.text(p, 161, y, 43, 21, '上次' if self.stale() else '剩余', 10, MUTED, align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.text(p, 207, y - 2, 64, 25, value, 18, color, True, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#494152'))
            p.drawRoundedRect(QRectF(29, y + 26, 242, 5), 2.5, 2.5)
            if remaining is not None and remaining > 0:
                p.setBrush(QColor(color))
                p.drawRoundedRect(QRectF(29, y + 26, max(3, 242 * remaining / 100), 5), 2.5, 2.5)
        if self.error:
            footer = '连接异常 · 点击查看处理方法'
        elif self.stale():
            footer = '上次数据 · 等待同步'
        else:
            footer = '收起详情' if self.expanded else '点击查看重置时间'
        self.text(p, 29, 331, 230, 19, footer, 10, MUTED)
        self.text(p, 255, 330, 17, 20, '⌃' if self.expanded else '⌄', 16, MUTED, align=Qt.AlignmentFlag.AlignCenter)
        if self.expanded:
            p.setPen(QPen(QColor('#494152'), 1))
            p.drawLine(QPointF(29, 359), QPointF(271, 359))
            for index, y in enumerate((369, 411)):
                window = (self.snapshot.primary, self.snapshot.secondary)[index] if self.snapshot else None
                self.text(p, 29, y, 242, 19, reset_text(window), 12, TEXT)
                label = window.label if window else ('主要额度' if index == 0 else '次要额度')
                self.text(p, 29, y + 18, 242, 17, f'{label} · {reset_date(window)}（本机时间）', 10, MUTED)
            if self.error:
                detail = self.error
                if self.snapshot:
                    detail += '；旧数据可能属于此前登录账号。'
            elif self.snapshot:
                stamp = datetime.fromtimestamp(self.snapshot.fetched_at).strftime('%H:%M:%S')
                detail = f'{self.snapshot.plan} · 上次更新 {stamp}\n每 2 分钟自动刷新 · 右键可调整桌宠'
            else:
                detail = '正在连接本机 Codex CLI…\n若未登录，请先在终端运行 codex login'
            self.text(p, 29, 454, 242, 48, detail, 10, '#e9bd81' if self.error else MUTED,
                      align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap)
        if self.bubble:
            p.setPen(QPen(QColor('#d3c7ec'), 1))
            p.setBrush(QColor('#f4eefc'))
            p.drawRoundedRect(QRectF(41, 3 - TOP_MARGIN, 218, 29), 14, 14)
            self.text(p, 49, 3 - TOP_MARGIN, 202, 29, self.bubble, 11, '#61507c', align=Qt.AlignmentFlag.AlignCenter)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        self._hover = event.position() / self.scale - QPointF(0, TOP_MARGIN)
        if self._press is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self._dragged = True
            if self._dragged:
                self.move(self._origin + delta)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position() / self.scale - QPointF(0, TOP_MARGIN)
        if self._dragged:
            self.clamp_position()
            self.save_position()
        elif self._press is not None:
            if QRectF(230, 211, 25, 27).contains(point):
                self.refresh()
            elif QRectF(258, 211, 23, 27).contains(point):
                self.open_menu(event.globalPosition().toPoint())
            elif point.y() >= CARD_TOP:
                self.expanded = not self.expanded
                self.resize_for_state()
                self.clamp_position()
            elif QRectF(*APPEARANCES[self.appearance].head_rect).contains(point):
                self.pat_head()
            else:
                self.show_bubble('按住拖动，就能带我换个位置。')
        self._press = None
        self._dragged = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def leaveEvent(self, event):
        self._hover = QPointF(-1, -1)
        self.update()

    def contextMenuEvent(self, event):
        self.open_menu(event.globalPos())

    def open_menu(self, position):
        menu = self.make_menu()
        menu.exec(position)
        menu.deleteLater()

    def make_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet('QMenu { background:#262132; color:#eee9f6; border:1px solid #554967; border-radius:8px; padding:6px; font:12px "Microsoft YaHei UI"; } QMenu::item { padding:7px 24px; border-radius:4px; } QMenu::item:selected { background:#514165; } QMenu::separator { height:1px; background:#4c4258; margin:5px; }')
        menu.addAction('显示桌宠', self.reveal)
        menu.addAction('刷新额度', self.refresh)
        menu.addSeparator()
        appearance_menu = menu.addMenu('切换形象')
        appearances = QActionGroup(appearance_menu)
        for key, definition in APPEARANCES.items():
            action = appearance_menu.addAction(definition.label)
            action.setCheckable(True)
            action.setChecked(self.appearance == key)
            appearances.addAction(action)
            action.triggered.connect(lambda checked=False, selected=key: self.change_appearance(selected))
        top = menu.addAction('始终置顶')
        top.setCheckable(True)
        top.setChecked(self.on_top)
        top.triggered.connect(self.toggle_top)
        motion = menu.addAction('轻微呼吸动画')
        motion.setCheckable(True)
        motion.setChecked(self.motion)
        motion.triggered.connect(self.toggle_motion)
        size_menu = menu.addMenu('桌宠大小')
        group = QActionGroup(size_menu)
        for value in (0.8, 1.0, 1.25, 1.5):
            action = size_menu.addAction(f'{value * 100:g}%')
            action.setCheckable(True)
            action.setChecked(self.scale == value)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, scale=value: self.change_scale(scale))
        menu.addAction('移回屏幕右下角', self.reset_position)
        menu.addSeparator()
        menu.addAction('选择 codex.exe…', self.choose_cli)
        menu.addAction('连接帮助', self.connection_help)
        menu.addAction('打开项目文件夹', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(project_root()))))
        if self.tray:
            menu.addAction('隐藏到托盘', self.hide)
        menu.addSeparator()
        menu.addAction('退出码伴', self.close)
        return menu

    def change_appearance(self, selected):
        if selected not in APPEARANCES:
            return
        sprite = QPixmap(str(asset_path(APPEARANCES[selected].asset)))
        if sprite.isNull():
            self.show_bubble('形象素材缺失，请保留完整的软件文件夹')
            return
        self.appearance = selected
        self.pet = sprite
        self._sprite_cache = None
        self._sprite_key = None
        self.pat_started = -100.0
        self.bubble = ''
        self.setWindowIcon(QIcon(self.pet))
        if self.tray:
            self.tray.setIcon(QIcon(self.pet))
        self.settings.update(appearance=selected)
        self.update_tray_menu()
        self.update()

    def toggle_top(self, checked):
        self.on_top = checked
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.settings.update(on_top=checked)
        self.reveal()
        self.update_tray_menu()

    def toggle_motion(self, checked):
        self.motion = checked
        self.settings.update(motion=checked)
        if checked and self.isVisible():
            self.animation.start()
        else:
            self.animation.stop()
        self.update_tray_menu()
        self.update()

    def change_scale(self, value):
        self.scale = value
        self.resize_for_state()
        self.clamp_position()
        self.settings.update(scale=value)
        self.update_tray_menu()

    def update_tray_menu(self):
        if self.tray:
            previous = self.tray.contextMenu()
            self.tray.setContextMenu(self.make_menu())
            if previous:
                previous.deleteLater()

    def choose_cli(self):
        if self.refreshing():
            self.show_bubble('正在读取，稍后再更换路径')
            return
        path, _ = QFileDialog.getOpenFileName(self, '选择 Codex CLI 的 codex.exe', '', 'Codex CLI (codex.exe)')
        if path:
            self.snapshot = None
            self.error = ''
            self.settings.update(cli_path=path)
            self.refresh()

    def connection_help(self):
        QMessageBox.information(self, '连接 Codex · 码伴',
            '码伴读取本机 Codex CLI 当前登录账号的额度。\n\n'
            '如果没有安装 CLI：在终端运行 npm install -g @openai/codex\n'
            '如果没有登录：在终端运行 codex login，使用 ChatGPT 账号登录。\n'
            '完成后点击卡片右上角的刷新按钮。\n\n'
            'CLI 账号可能与 Codex 桌面应用中的账号不同，请使用同一个账号。\n'
            '也可以右键“选择 codex.exe”指定已安装的原生 CLI。\n\n'
            '两条额度来自服务返回的窗口；缺失数据会显示 —。\n'
            '刷新只查询额度；摸头和动画由本地程序完成。')

    def tray_activate(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.reveal()

    def reveal(self):
        self.show()
        self.clamp_position()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        if hasattr(self, 'animation') and self.motion:
            self.animation.start()
        super().showEvent(event)

    def hideEvent(self, event):
        if hasattr(self, 'animation'):
            self.animation.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.closing = True
        self.refresh_timer.stop()
        self.animation.stop()
        self.clock.stop()
        if self.worker and self.worker.isRunning():
            self.worker.cancel.set()
            # Worker polls every 100 ms and owns a bounded subprocess shutdown.
            if not self.worker.wait(3500):
                event.ignore()
                self.show_bubble('正在关闭连接…')
                QTimer.singleShot(300, self.close)
                return
        self.save_position()
        if self.tray:
            self.tray.hide()
        event.accept()
        QApplication.instance().quit()


class SingleInstance:
    def __init__(self, window):
        self.window = window
        self.name = 'codexpet-desktop-v1'
        self.lock = QLockFile(str(data_dir() / 'instance.lock'))
        self.lock.setStaleLockTime(0)
        self.server = None

    def acquire(self):
        if not self.lock.tryLock(100):
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if socket.waitForConnected(1000):
                socket.write(b'show\n')
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not self.server.listen(self.name):
            self.lock.unlock()
            return False
        self.server.newConnection.connect(self.on_connection)
        return True

    def on_connection(self):
        socket = self.server.nextPendingConnection()
        if socket:
            self.window.reveal()
            socket.disconnectFromServer()
            socket.deleteLater()

    def close(self):
        if self.server:
            self.server.close()
        self.lock.unlock()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', help='Clearly labelled offline sample data')
    parser.add_argument('--appearance', choices=APPEARANCES, help='Select and remember a pet appearance')
    parser.add_argument('--preview', type=Path, help='Render a labelled demo PNG and exit')
    parser.add_argument('--check', type=Path, help='Run one real read, save redacted health report and PNG, then exit')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('CodexPet')
    app.setOrganizationName('CodexPet')
    app.setQuitOnLastWindowClosed(False)
    diagnostic = bool(args.preview or args.check)
    settings = Settings((args.preview or args.check).parent / 'diagnostic-settings.json') if diagnostic else Settings()
    if args.appearance:
        settings.update(appearance=args.appearance)
    window = PetWindow(settings, online=not (args.demo or args.preview), demo=bool(args.demo or args.preview), tray=not diagnostic)
    guard = None
    if not diagnostic:
        guard = SingleInstance(window)
        if not guard.acquire():
            return 0
        app.aboutToQuit.connect(guard.close)
    window.show()
    if args.preview:
        def render():
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.preview))
            window.close()
        QTimer.singleShot(250, render)
    if args.check:
        check_started = time.monotonic()
        def report():
            if not window.snapshot and not window.error and time.monotonic() - check_started < 32:
                QTimer.singleShot(150, report)
                return
            args.check.parent.mkdir(parents=True, exist_ok=True)
            snap = window.snapshot
            result = {'ok': bool(snap), 'error': window.error, 'assetLoaded': not window.pet.isNull(), 'appearance': window.appearance, 'frozen': bool(getattr(sys, 'frozen', False)),
                      'primaryRemaining': snap.primary.remaining if snap and snap.primary else None,
                      'secondaryRemaining': snap.secondary.remaining if snap and snap.secondary else None}
            args.check.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            window.expanded = True
            window.resize_for_state()
            window.grab().save(str(args.check.with_suffix('.png')))
            window.close()
        QTimer.singleShot(500, report)
    return app.exec()
