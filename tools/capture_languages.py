"""Render actual localized windows with offline sample data only."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from codexpet.app import PetWindow
from codexpet.settings import Settings

root = Path(__file__).resolve().parents[1]
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
for language in ('en', 'tr'):
    settings = Settings(root / 'build' / f'preview-{language}.json')
    settings.update(language=language, appearance='chibi', scale=1.25, motion=False)
    pet = PetWindow(settings, online=False, demo=True, tray=False)
    pet.expanded = True
    pet.resize_for_state()
    pet.show()
    pet.pat_head()
    QTest.qWait(100)
    pet.grab().save(str(root / 'docs' / f'preview-{language}.png'))
    pet.open_connection()
    QTest.qWait(100)
    pet.connection_dialog.grab().save(str(root / 'docs' / f'preview-connection-{language}.png'))
    pet.connection_dialog.reject()
    pet.close()
    pet.deleteLater()
    app.processEvents()
