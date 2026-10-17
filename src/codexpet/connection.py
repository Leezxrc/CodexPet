"""One-click setup: official portable CLI, existing login, or browser OAuth.

Passwords, auth files, account objects and login process output are never read
or persisted by the pet. The official CLI owns OAuth and credential storage.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import zipfile

from .client import Cancelled, UsageError, fetch_usage, find_codex, read_login_state
from .settings import data_dir

RELEASE_API = 'https://api.github.com/repos/openai/codex/releases/latest'
MAX_DOWNLOAD = 350 * 1024 * 1024


class ChatGPTLoginRequired(UsageError):
    pass


def checkpoint(cancel):
    if cancel.is_set():
        raise Cancelled('连接已取消')


def get_response(url):
    parsed = urlparse(url)
    allowed = {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
    if parsed.scheme != 'https' or parsed.hostname not in allowed:
        raise UsageError('官方安装包地址校验失败')
    response = urlopen(Request(url, headers={'User-Agent': 'CodexPet', 'Accept': 'application/vnd.github+json'}), timeout=8)
    final = urlparse(response.geturl())
    if final.scheme != 'https' or final.hostname not in allowed:
        response.close()
        raise UsageError('官方安装包下载地址不受支持')
    return response


def select_assets(metadata, machine=None):
    machine = (machine or os.environ.get('PROCESSOR_ARCHITEW6432') or platform.machine()).lower()
    architecture = {'amd64': 'x86_64', 'x86_64': 'x86_64', 'arm64': 'aarch64', 'aarch64': 'aarch64'}.get(machine)
    if not architecture:
        raise UsageError('自动安装支持 Windows x64 和 ARM64，请手动选择 codex.exe')
    tag = metadata.get('tag_name', '')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', tag):
        raise UsageError('官方版本信息无效，请稍后重试')
    available = {a.get('name'): a for a in metadata.get('assets', []) if isinstance(a, dict)}
    selected = []
    for program in ('codex', 'codex-app-server'):
        name = f'{program}-{architecture}-pc-windows-msvc.exe.zip'
        asset = available.get(name)
        if not asset:
            if program == 'codex':
                raise UsageError('官方版本没有提供此系统的安装包')
            continue  # Older monolithic CLIs have no separate app-server.
        url = asset.get('browser_download_url', '')
        digest = asset.get('digest', '')
        if not url.startswith(f'https://github.com/openai/codex/releases/download/{tag}/') or url.rsplit('/', 1)[-1] != name:
            raise UsageError('官方安装包来源校验失败')
        if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            raise UsageError('官方安装包暂未提供校验值，请稍后重试或手动安装 CLI')
        selected.append((program, asset))
    return tag, selected


def unpack_verified(archive, destination, program, asset, cancel):
    checkpoint(cancel)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != asset['digest'][7:].lower():
        raise UsageError('下载校验失败，请重试；未安装该文件')
    with zipfile.ZipFile(archive) as bundle:
        # Copy only the known executable to a fixed filename, never extract paths.
        expected = asset['name'][:-4]
        matches = [i for i in bundle.infolist() if not i.is_dir() and Path(i.filename).name in (expected, program + '.exe')]
        if len(matches) != 1 or matches[0].file_size > 700 * 1024 * 1024:
            raise UsageError('官方安装包内容不受支持，请手动安装 CLI')
        with bundle.open(matches[0]) as src, (destination / (program + '.exe')).open('wb') as dst:
            while chunk := src.read(1024 * 1024):
                checkpoint(cancel)
                dst.write(chunk)


def install_cli(cancel, progress, root=None):
    root = Path(root) if root else data_dir() / 'runtime' / 'codex'
    checkpoint(cancel)
    progress('正在获取 OpenAI 官方 CLI 安装信息…')
    try:
        with get_response(RELEASE_API) as response:
            metadata = json.loads(response.read(2 * 1024 * 1024))
        tag, assets = select_assets(metadata)
        root.mkdir(parents=True, exist_ok=True)
        destination = root / tag
        if all((destination / (name + '.exe')).is_file() for name, _ in assets):
            return destination / 'codex.exe'
        with tempfile.TemporaryDirectory(prefix='install-', dir=root) as scratch:
            staging = Path(scratch) / 'ready'
            staging.mkdir()
            deadline = time.monotonic() + 600
            for program, asset in assets:
                checkpoint(cancel)
                archive = Path(scratch) / 'download.zip'
                received = 0
                last_mb = -1
                with get_response(asset['browser_download_url']) as response, archive.open('wb') as stream:
                    while chunk := response.read(256 * 1024):
                        checkpoint(cancel)
                        received += len(chunk)
                        if received > MAX_DOWNLOAD or time.monotonic() > deadline:
                            raise UsageError('下载超过大小或时间限制，请检查网络后重试')
                        stream.write(chunk)
                        mb = received // (1024 * 1024)
                        if mb != last_mb:
                            progress(f'正在下载 {program}：{mb} MB（首次连接需要）')
                            last_mb = mb
                progress(f'正在校验并准备 {program}…')
                unpack_verified(archive, staging, program, asset, cancel)
            checkpoint(cancel)
            staging.rename(destination)
        return destination / 'codex.exe'
    except (Cancelled, UsageError):
        raise
    except Exception as exc:
        raise UsageError('自动安装未完成，请检查网络后重试，或在菜单中手动选择 codex.exe') from exc


def browser_login(executable, cancel, timeout=300, process_factory=subprocess.Popen, command=None):
    checkpoint(cancel)
    try:
        proc = process_factory(command or [str(executable), 'login'], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError as exc:
        raise UsageError('无法启动官方登录，请重试或手动运行 codex login') from exc
    try:
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            checkpoint(cancel)
            if time.monotonic() > deadline:
                raise UsageError('登录等待超时，请重试并在浏览器中完成授权')
            cancel.wait(0.1)
        checkpoint(cancel)
        if proc.returncode != 0:
            raise UsageError('登录未完成。请重试；若浏览器未打开，可手动运行 codex login')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1)


def connect_account(override='', cancel=None, progress=lambda _: None, replace_login=False):
    cancel = cancel or threading.Event()
    checkpoint(cancel)
    progress('正在检测本机 Codex…')
    try:
        executable = find_codex(override)
    except UsageError:
        if override:
            # A saved path may have moved; re-run auto-detection before installing.
            try:
                executable = find_codex()
            except UsageError:
                executable = install_cli(cancel, progress)
        else:
            executable = install_cli(cancel, progress)
    progress('正在检查登录状态…')
    state = 'signed_out' if replace_login else read_login_state(str(executable), cancel)
    if state == 'other' and not replace_login:
        raise ChatGPTLoginRequired('当前 CLI 使用其他登录方式。点击“使用 ChatGPT 登录”将切换 CLI 登录，以读取套餐额度。')
    if state != 'chatgpt' or replace_login:
        progress('请在浏览器完成 ChatGPT 登录，完成后这里会自动连接。最多等待 5 分钟。')
        browser_login(executable, cancel)
        if read_login_state(str(executable), cancel) != 'chatgpt':
            raise UsageError('未检测到 ChatGPT 登录，请重试或检查 CLI 的登录配置')
    progress('正在验证额度连接…')
    snapshot = fetch_usage(str(executable), cancel)
    checkpoint(cancel)
    return str(executable), snapshot
