"""Shared filesystem utilities: size formatting, scanning, safe
execution wrapper (dry-run aware), and deletion helpers.

Used by nearly every feature module.
"""
import os
import shutil
import subprocess
import re
from pathlib import Path

from core import state
from core.sudo import check_sudo_status
from ui.colors import YELLOW, RED, GREEN, BOLD, DIM, RESET
from ui.terminal import center_print, _divider


def format_size(b: int) -> str:
    if b <= 0:
        return "0 B"
    size = float(b)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def _walk_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() and not path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    try:
        out = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return int(out.stdout.split()[0])
    except Exception:
        pass
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file() and not f.is_symlink():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except Exception:
        pass
    return total


def scan_described_paths(targets: list[dict]) -> list[dict]:
    for t in targets:
        p    = Path(t["path"])
        size = _walk_size(p) if p.exists() else 0
        t.update({
            "size_bytes": size,
            "size_fmt":   format_size(size),
            "exists":     p.exists(),
        })
    return targets


def print_described_table(targets: list[dict], title: str = "") -> int:
    if title:
        center_print(f"{BOLD}{title}{RESET}")
        print()
    total = 0
    for t in targets:
        if t["exists"]:
            status = f"{YELLOW}{BOLD}{t['size_fmt']}{RESET}"
        else:
            status = f"{DIM}Not Found{RESET}"

        importance = f"{RED}{BOLD}[IMPORTANT]{RESET} " if t.get("is_important") else ""
        center_print(f"  {DIM}→{RESET}  {t['label']:<32}  {status}")
        center_print(f"     {DIM}{importance}{t['desc']}{RESET}")
        print()

        if t["exists"]:
            total += t["size_bytes"]

    _divider()
    color = GREEN if total == 0 else YELLOW
    center_print(f"  Total footprint:  {color}{BOLD}{format_size(total)}{RESET}")
    print()
    return total


def _run(cmd: list[str], use_sudo: bool = False) -> bool:
    if use_sudo and cmd[0] != 'sudo':
        cmd = ['sudo'] + cmd
    if state.IS_DRY_RUN:
        center_print(f"    {DIM}[DRY RUN] Would execute: {' '.join(cmd)}{RESET}")
        return True
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def delete_path_content(path: Path, delete_root: bool = False) -> bool:
    if not path.exists(): return True
    if state.IS_DRY_RUN:
        target = "file" if path.is_file() else "directory"
        center_print(f"    {DIM}[DRY RUN] Would delete {target}: {path}{RESET}")
        return True
    sudo = check_sudo_status()
    try:
        if path.is_file() or path.is_symlink():
            if sudo: return _run(['rm', '-f', str(path)], use_sudo=True)
            path.unlink(); return True
        if delete_root:
            if sudo: return _run(['rm', '-rf', str(path)], use_sudo=True)
            shutil.rmtree(path, ignore_errors=True); return True
        ok = True
        for child in path.iterdir():
            try:
                if child.is_dir() and not child.is_symlink():
                    if sudo: ok &= _run(['rm', '-rf', str(child)], use_sudo=True)
                    else: shutil.rmtree(child, ignore_errors=True)
                else:
                    if sudo: ok &= _run(['rm', '-f', str(child)], use_sudo=True)
                    else: child.unlink(missing_ok=True)
            except OSError: ok = False
        return ok
    except PermissionError: return False


def _find_recursive_targets(root: Path, name_pattern: str, skip_folders: set[str] = None) -> tuple[list[Path], int]:
    if skip_folders is None:
        skip_folders = {'.cache', '.local', '.git', 'venv', '.venv', 'node_modules', 'Downloads'}
    found: list[Path] = []
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_folders and not d.startswith('.')]
        if name_pattern == "__pycache__":
            if "__pycache__" in dirnames:
                p = Path(dirpath) / "__pycache__"
                found.append(p)
                total_size += _walk_size(p)
        else:  # Generic file search (like broken symlinks)
            for f in filenames:
                fp = Path(dirpath) / f
                if fp.is_symlink() and not fp.exists():
                    found.append(fp)
    return found, total_size


def _find_dead_logs(root: Path) -> tuple[list[Path], int]:
    found: list[Path] = []
    total = 0
    pattern = re.compile(r'.*\.(gz|\d+|old)$')
    try:
        for f in root.rglob("*"):
            if f.is_file() and pattern.match(f.name):
                found.append(f); total += f.stat().st_size
    except Exception: pass
    return found, total
