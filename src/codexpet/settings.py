import json
import os
from pathlib import Path
import sys


def project_root():
    if getattr(sys, 'frozen', False):
        # app/CodexPet/CodexPet.exe -> project folder
        return Path(sys.executable).resolve().parents[2]
    return Path(__file__).resolve().parents[2]


def data_dir():
    candidates = [project_root() / 'data', Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CodexPet']
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / '.write-probe'
            probe.write_text('', encoding='utf-8')
            probe.unlink()
            return path
        except OSError:
            continue
    return candidates[-1]


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / 'settings.json'
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            self.values = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def update(self, **values):
        self.values.update(values)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.path)
            return True
        except OSError:
            return False
