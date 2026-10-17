from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from codexpet.app import PetWindow, EXPANDED_HEIGHT, COMPACT_HEIGHT, TOP_MARGIN
from codexpet.settings import Settings


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / 'build' / 'test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.pet = PetWindow(Settings(Path(self.temp.name) / 'settings.json'), online=False, demo=True, tray=False)
        self.pet.show()
        QTest.qWait(30)

    def tearDown(self):
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_details_toggle_and_scaled_hit_test(self):
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(150, 340 + TOP_MARGIN))
        self.assertTrue(self.pet.expanded)
        self.assertEqual(self.pet.height(), EXPANDED_HEIGHT + TOP_MARGIN)
        self.pet.change_scale(1.5)
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(225, 510 + int(TOP_MARGIN * 1.5)))
        self.assertFalse(self.pet.expanded)
        self.assertEqual(self.pet.height(), int((COMPACT_HEIGHT + TOP_MARGIN) * 1.5))

    def test_head_pat_has_local_feedback(self):
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(150, 65 + TOP_MARGIN))
        self.assertTrue(self.pet.bubble)
        self.assertLess(time.monotonic() - self.pet.pat_started, 1)
        self.assertIsNone(self.pet.worker)

    def test_drag_does_not_trigger_head_pat(self):
        start = self.pet.pos()
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(150, 65 + TOP_MARGIN))
        QTest.mouseMove(self.pet, QPoint(120, 35 + TOP_MARGIN), delay=30)
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(120, 35 + TOP_MARGIN))
        self.assertFalse(self.pet.bubble)
        self.assertNotEqual(self.pet.pos(), start)
        self.assertIsNotNone(self.pet.settings.get('x'))

    def test_failure_retains_but_marks_old_data(self):
        self.pet.demo = False
        snap = self.pet.snapshot
        self.pet.on_failure('network')
        self.assertIs(self.pet.snapshot, snap)
        self.assertTrue(self.pet.stale())
        self.assertEqual(self.pet.status()[0], '旧数据')

    def test_hidden_animation_stops_and_reveal_restores(self):
        self.pet.hide()
        self.assertFalse(self.pet.animation.isActive())
        self.pet.reveal()
        self.assertTrue(self.pet.isVisible())
        self.assertTrue(self.pet.animation.isActive())

    def test_appearance_menu_switches_and_persists_without_resetting_quota(self):
        snapshot = self.pet.snapshot
        position = self.pet.pos()
        menu = self.pet.make_menu()
        submenu = next(a.menu() for a in menu.actions() if a.text() == '切换形象')
        action = next(a for a in submenu.actions() if 'Q 版' in a.text())
        action.trigger()
        self.app.processEvents()
        self.assertEqual(self.pet.appearance, 'chibi')
        self.assertEqual(self.pet.pet.width(), self.pet.pet.height())
        self.assertIs(self.pet.snapshot, snapshot)
        self.assertEqual(self.pet.pos(), position)
        self.assertEqual(Settings(self.pet.settings.path).get('appearance'), 'chibi')
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(150, TOP_MARGIN + 120))
        self.assertTrue(self.pet.bubble)
        replacement = PetWindow(Settings(self.pet.settings.path), online=False, tray=False)
        self.assertEqual(replacement.appearance, 'chibi')
        replacement.close()
        replacement.deleteLater()
        menu.deleteLater()
        self.pet.change_appearance('dragon')
        self.assertEqual(self.pet.appearance, 'dragon')
        self.assertFalse(self.pet.bubble)

    def test_unknown_saved_appearance_falls_back(self):
        settings = Settings(Path(self.temp.name) / 'unknown.json')
        settings.update(appearance=['invalid'])
        replacement = PetWindow(settings, online=False, tray=False)
        self.assertEqual(replacement.appearance, 'dragon')
        replacement.close()
        replacement.deleteLater()

    def test_one_click_connection_saves_path_and_updates_quota(self):
        snapshot = self.pet.snapshot
        self.pet.open_connection()
        dialog = self.pet.connection_dialog
        with patch('codexpet.connection_dialog.connect_account', return_value=('test-codex.exe', snapshot)) as connect:
            QTest.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)
            for _ in range(30):
                QTest.qWait(20)
                if not dialog.busy():
                    break
            self.assertFalse(dialog.busy())
            connect.assert_called_once()
            self.assertIn('连接成功', dialog.status_label.text())
            self.assertEqual(self.pet.settings.get('cli_path'), 'test-codex.exe')
            self.assertIs(self.pet.snapshot, snapshot)
        dialog.reject()


if __name__ == '__main__':
    unittest.main()
