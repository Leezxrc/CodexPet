from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.client import Cancelled, UsageError, fetch_usage


class ClientTests(unittest.TestCase):
    def request(self, mode, **kwargs):
        self.processes = []
        def factory(*args, **options):
            proc = subprocess.Popen(*args, **options)
            self.processes.append(proc)
            return proc
        return fetch_usage(command=[sys.executable, '-u', str(Path(__file__).with_name('fake_server.py')), mode], process_factory=factory, **kwargs)

    def tearDown(self):
        for proc in getattr(self, 'processes', []):
            self.assertIsNotNone(proc.poll(), 'Client left a subprocess running')

    def test_handshake_ids_noise_and_read_only_request(self):
        self.assertEqual(self.request('ok').primary.remaining, 58)

    def test_auth_message_redacted(self):
        with self.assertRaises(UsageError) as error:
            self.request('auth')
        self.assertIn('codex login', str(error.exception))
        self.assertNotIn('secret', str(error.exception))

    def test_eof_is_bounded(self):
        start = time.monotonic()
        with self.assertRaises(UsageError):
            self.request('eof')
        self.assertLess(time.monotonic() - start, 3)

    def test_timeout_reaps_process(self):
        start = time.monotonic()
        with self.assertRaisesRegex(UsageError, '超时'):
            self.request('hang', timeout=0.3)
        self.assertLess(time.monotonic() - start, 3)

    def test_cancel_reaps_process(self):
        cancel = threading.Event()
        timer = threading.Timer(0.2, cancel.set)
        timer.start()
        try:
            with self.assertRaises(Cancelled):
                self.request('hang', cancel=cancel)
        finally:
            timer.cancel()


if __name__ == '__main__':
    unittest.main()
