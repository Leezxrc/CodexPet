from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet import connection as c
from codexpet.client import read_login_state


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.cancel = threading.Event()

    def test_existing_chatgpt_login_is_reused_without_login_or_install(self):
        snapshot = object()
        with patch.object(c, 'find_codex', return_value=Path('codex.exe')), \
             patch.object(c, 'read_login_state', return_value='chatgpt'), \
             patch.object(c, 'fetch_usage', return_value=snapshot), \
             patch.object(c, 'browser_login') as login, patch.object(c, 'install_cli') as install:
            path, received = c.connect_account()
            self.assertIs(received, snapshot)
            self.assertEqual(path, 'codex.exe')
            login.assert_not_called()
            install.assert_not_called()

    def test_missing_cli_and_signed_out_account_are_configured_in_order(self):
        with patch.object(c, 'find_codex', side_effect=c.UsageError('missing')), \
             patch.object(c, 'install_cli', return_value=Path('managed/codex.exe')) as install, \
             patch.object(c, 'read_login_state', side_effect=['signed_out', 'chatgpt']), \
             patch.object(c, 'browser_login') as login, patch.object(c, 'fetch_usage', return_value='snapshot'):
            path, snapshot = c.connect_account(cancel=self.cancel)
            self.assertEqual(snapshot, 'snapshot')
            self.assertTrue(path.endswith('codex.exe'))
            install.assert_called_once()
            login.assert_called_once()

    def test_other_login_requires_explicit_switch_and_network_errors_do_not_relogin(self):
        with patch.object(c, 'find_codex', return_value=Path('codex.exe')), \
             patch.object(c, 'read_login_state', return_value='other'), \
             patch.object(c, 'browser_login') as login:
            with self.assertRaises(c.ChatGPTLoginRequired):
                c.connect_account()
            login.assert_not_called()
        with patch.object(c, 'find_codex', return_value=Path('codex.exe')), \
             patch.object(c, 'read_login_state', side_effect=c.UsageError('network')), \
             patch.object(c, 'browser_login') as login:
            with self.assertRaises(c.UsageError):
                c.connect_account()
            login.assert_not_called()

    def test_explicit_switch_verifies_login_before_reading_quota(self):
        with patch.object(c, 'find_codex', return_value=Path('codex.exe')), \
             patch.object(c, 'read_login_state', return_value='chatgpt') as state, \
             patch.object(c, 'browser_login') as login, patch.object(c, 'fetch_usage', return_value='ok'):
            self.assertEqual(c.connect_account(replace_login=True)[1], 'ok')
            login.assert_called_once()
            state.assert_called_once()

    def test_login_cancel_and_timeout_reap_only_owned_process(self):
        for cancel_after in (None, 0.15):
            created = []
            def factory(*args, **kwargs):
                proc = subprocess.Popen(*args, **kwargs)
                created.append(proc)
                return proc
            self.cancel.clear()
            timer = threading.Timer(cancel_after, self.cancel.set) if cancel_after else None
            if timer:
                timer.start()
            try:
                with self.assertRaises(c.UsageError):
                    c.browser_login('unused', self.cancel, timeout=0.3, process_factory=factory,
                                    command=[sys.executable, '-c', 'import time; time.sleep(60)'])
                self.assertIsNotNone(created[0].poll())
            finally:
                if timer:
                    timer.cancel()

    def test_selects_correct_official_windows_assets_and_rejects_bad_metadata(self):
        name = 'codex-x86_64-pc-windows-msvc.exe.zip'
        asset = {'name': name, 'digest': 'sha256:' + '0' * 64,
                 'browser_download_url': 'https://github.com/openai/codex/releases/download/v1/' + name}
        metadata = {'tag_name': 'v1', 'assets': [asset]}
        self.assertEqual(c.select_assets(metadata, 'AMD64')[1][0][0], 'codex')
        for key, value in [('tag_name', '../escape'), ('tag_name', '..'), ('assets', [dict(asset, digest=None)]),
                           ('assets', [dict(asset, browser_download_url='https://example.com/file.zip')])]:
            with self.subTest(key=key), self.assertRaises(c.UsageError):
                c.select_assets(dict(metadata, **{key: value}), 'AMD64')
        with self.assertRaises(c.UsageError):
            c.select_assets(metadata, 'ARM64')

    def test_zip_checksum_and_fixed_destination(self):
        scratch = Path(__file__).resolve().parents[1] / 'build' / 'test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            archive = root / 'payload.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('codex.exe', b'MZ-test')
                bundle.writestr('../escape.txt', b'never extracted')
            asset = {'name': 'codex-x86_64-pc-windows-msvc.exe.zip',
                     'digest': 'sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest()}
            target = root / 'ready'
            target.mkdir()
            c.unpack_verified(archive, target, 'codex', asset, self.cancel)
            self.assertEqual((target / 'codex.exe').read_bytes(), b'MZ-test')
            self.assertFalse((root / 'escape.txt').exists())
            (target / 'codex.exe').unlink()
            asset['digest'] = 'sha256:' + '0' * 64
            with self.assertRaises(c.UsageError):
                c.unpack_verified(archive, target, 'codex', asset, self.cancel)
            self.assertFalse((target / 'codex.exe').exists())

    def test_login_state_uses_account_protocol_without_returning_account_details(self):
        for mode, expected in [('account', 'chatgpt'), ('signed_out', 'signed_out'), ('api_key', 'other')]:
            state = read_login_state(command=[sys.executable, '-u', str(Path(__file__).with_name('fake_server.py')), mode])
            self.assertEqual(state, expected)


if __name__ == '__main__':
    unittest.main()
