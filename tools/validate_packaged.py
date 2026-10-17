"""Validate the shipped app in an isolated runtime environment."""
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
exe = root / 'app' / 'CodexPet' / 'CodexPet.exe'
report_path = root / 'docs' / 'packaged-live-check.json'
env = dict(os.environ)
for key in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM', 'QML2_IMPORT_PATH'):
    env.pop(key, None)
env['PATH'] = os.path.join(env.get('SystemRoot', 'C:\\Windows'), 'System32') + os.pathsep + env.get('SystemRoot', 'C:\\Windows')
start = time.time()
checked = subprocess.Popen([str(exe), '--check', str(report_path)], cwd=exe.parent, env=env)
try:
    checked.wait(timeout=40)
finally:
    if checked.poll() is None:
        checked.terminate()
        checked.wait(timeout=5)
assert checked.returncode == 0, checked.returncode
assert report_path.stat().st_mtime >= start - 1, 'No fresh diagnostic report'
report = json.loads(report_path.read_text(encoding='utf-8'))
assert report['ok'] and report['frozen'] and report['assetLoaded'], report
print('PACKAGED_LIVE_READ', json.dumps(report, ensure_ascii=True))

# Demo mode never starts a Codex subprocess, so these owned test processes may
# be terminated to simulate a crash and exercise stale-lock recovery safely.
first = subprocess.Popen([str(exe), '--demo'], cwd=exe.parent, env=env)
try:
    time.sleep(1.2)
    assert first.poll() is None, 'First instance did not stay open'
    second = subprocess.Popen([str(exe), '--demo'], cwd=exe.parent, env=env)
    try:
        second.wait(timeout=5)
        assert second.returncode == 0, 'Second launch failed to activate existing pet'
        assert first.poll() is None
    finally:
        if second.poll() is None:
            second.terminate()
            second.wait(timeout=5)
finally:
    if first.poll() is None:
        first.terminate()
        first.wait(timeout=5)
third = subprocess.Popen([str(exe), '--demo'], cwd=exe.parent, env=env)
try:
    time.sleep(1.2)
    assert third.poll() is None, 'Stale-lock recovery failed'
finally:
    if third.poll() is None:
        third.terminate()
        third.wait(timeout=5)
report['singleInstancePassed'] = True
report['staleLockRecoveryPassed'] = True
report['cleanRuntimePassed'] = True
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SINGLE_INSTANCE_AND_CRASH_RECOVERY_OK')
