"""Render the real UI's offline demonstration states for visual QA."""
from pathlib import Path
from decimal import Decimal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from codexpet.app import PetWindow
from codexpet.settings import Settings
from codexpet.quota import Snapshot, Window

root = Path(__file__).resolve().parents[1]
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
window = PetWindow(Settings(root / 'build' / 'visual-settings.json'), online=False, demo=True, tray=False)
window.change_appearance('dragon')
window.scale = 1.25
window.resize_for_state()
window.show()
QTest.qWait(120)

def save(name):
    # Composite the UI capture on a neutral desktop-like background for viewing.
    shot = window.grab().toImage()
    canvas = QImage(shot.width() + 60, shot.height() + 60, QImage.Format.Format_ARGB32)
    canvas.fill(QColor('#e9e5f1'))
    painter = QPainter(canvas)
    painter.drawImage(30, 30, shot)
    painter.end()
    canvas.save(str(root / 'docs' / name))

save('preview-compact.png')
window.pat_head()
QTest.qWait(280)
save('preview-petting.png')
window.bubble = ''
window.pat_started = -100
window.expanded = True
window.resize_for_state()
QTest.qWait(50)
save('preview-details.png')
window.demo = False
window.on_failure('暂时无法连接 Codex 服务，请检查网络后刷新')
QTest.qWait(50)
save('preview-stale.png')
window.snapshot = None
QTest.qWait(50)
save('preview-unavailable.png')
window.demo = True
now = time.time()
window.on_success(Snapshot(Window(34, 300, now + 7260), Window(5, 10080, now + 365400), 'Plus', now, 2, Decimal('128.50')))
window.expanded = False
window.resize_for_state()
window.change_appearance('chibi')
QTest.qWait(50)
save('preview-chibi.png')
window.pat_head()
QTest.qWait(230)
save('preview-chibi-petting.png')
window.close()
