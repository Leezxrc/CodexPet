"""Capture the actual setup dialog's neutral initial state, without signing in."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from codexpet.connection_dialog import ConnectionDialog
from codexpet.settings import Settings

root = Path(__file__).resolve().parents[1]
app = QApplication([])
dialog = ConnectionDialog(Settings(root / 'build' / 'connection-preview-settings.json'))
dialog.show()
QTest.qWait(100)
dialog.grab().save(str(root / 'docs' / 'preview-connection.png'))
dialog.close()
