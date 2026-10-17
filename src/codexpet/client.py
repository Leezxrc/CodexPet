"""Read-only Codex app-server client; never reads or copies credential files."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

from .quota import parse_snapshot
from . import __version__


class UsageError(Exception):
    pass


class Cancelled(UsageError):
    pass


def find_codex(override=''):
    explicit = override or os.environ.get('CODEXPET_CODEX_EXE', '')
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file() and path.name.lower() == 'codex.exe':
            return path
        raise UsageError('设置中的 codex.exe 路径不可用，请右键重新选择')
    native = shutil.which('codex.exe')
    if native:
        return Path(native)
    roots = [Path(os.environ.get('APPDATA', Path.home())) / 'npm']
    for command in ('codex.cmd', 'codex.ps1', 'codex'):
        found = shutil.which(command)
        if found:
            roots.append(Path(found).parent)
    for root in dict.fromkeys(roots):
        for architecture, triple in (('x64', 'x86_64'), ('arm64', 'aarch64')):
            path = root / f'node_modules/@openai/codex/node_modules/@openai/codex-win32-{architecture}/vendor/{triple}-pc-windows-msvc/bin/codex.exe'
            if path.is_file():
                return path
    raise UsageError('未找到 Codex CLI：请安装并登录，或右键选择 codex.exe')


def _public_error(error):
    # Only classify server messages. Never expose raw messages, tokens, or config values.
    message = str(error.get('message', '')).lower() if isinstance(error, dict) else ''
    if any(word in message for word in ('auth', 'login', 'logged', 'sign in', 'token', '401', '403')):
        return '登录状态不可用：请在终端运行 codex login，再点击刷新'
    if any(word in message for word in ('network', 'connect', 'request', 'timeout', 'fetch', 'dns')):
        return '暂时无法连接 Codex 服务，请检查网络后刷新'
    return 'Codex 未能返回额度，请检查 CLI 登录状态或更新 CLI'


def fetch_usage(override='', cancel=None, timeout=25.0, process_factory=subprocess.Popen, command=None):
    cancel = cancel or threading.Event()
    if cancel.is_set():
        raise Cancelled('已取消')
    cmd = command or [str(find_codex(override)), 'app-server', '--listen', 'stdio://']
    deadline = time.monotonic() + timeout
    try:
        proc = process_factory(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                               errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError as exc:
        raise UsageError('无法启动 Codex CLI，请检查 codex.exe 路径') from exc
    incoming = queue.Queue(maxsize=128)
    stopped = threading.Event()

    def read_stdout():
        try:
            while not stopped.is_set():
                line = proc.stdout.readline(1024 * 1024)
                if not line:
                    incoming.put_nowait(None)
                    return
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        incoming.put_nowait(value)
                except (ValueError, queue.Full):
                    continue
        except (OSError, ValueError, queue.Full):
            return

    reader = threading.Thread(target=read_stdout, daemon=True, name='codexpet-rpc-reader')
    reader.start()

    def send(value):
        try:
            proc.stdin.write(json.dumps(value) + '\n')
            proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise UsageError('Codex 连接已中断，请刷新重试') from exc

    def receive(identifier):
        while time.monotonic() < deadline:
            if cancel.is_set():
                raise Cancelled('已取消')
            try:
                value = incoming.get(timeout=0.1)
            except queue.Empty:
                if proc.poll() is not None:
                    raise UsageError('Codex 服务未能启动，请检查 CLI 配置与登录状态')
                continue
            if value is None:
                raise UsageError('Codex 连接已关闭，请刷新重试')
            if value.get('id') == identifier and 'method' not in value:
                if 'error' in value:
                    raise UsageError(_public_error(value['error']))
                return value.get('result')
            if 'method' in value and 'id' in value:
                send({'id': value['id'], 'error': {'code': -32601, 'message': 'This client supports quota reads only'}})
        raise UsageError('读取额度超时，稍后会自动重试')

    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'codex_pet', 'title': 'CodexPet', 'version': __version__}}})
        receive(1)
        send({'method': 'initialized', 'params': {}})
        send({'id': 2, 'method': 'account/rateLimits/read'})
        result = receive(2)
        try:
            return parse_snapshot(result)
        except ValueError as exc:
            raise UsageError(str(exc)) from exc
    finally:
        stopped.set()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1)
        reader.join(timeout=0.5)
        for pipe in (proc.stdin, proc.stdout):
            if pipe:
                pipe.close()
