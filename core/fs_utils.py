"""Shared filesystem utilities: size formatting, scanning, safe
execution wrapper (dry-run aware), and deletion helpers.

Used by nearly every feature module.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

from core import state
from core.sudo import check_sudo_status, get_user_home
from ui.colors import BOLD, DIM, GREEN, RED, RESET, YELLOW
from ui.terminal import _divider, center_print

# Directories that must never be deleted, no matter what feature or
# scan produced the path. Checked against the *resolved* path (i.e.
# after following any symlink), so a symlink planted inside an
# otherwise-allowed cache directory that points into one of these
# cannot be used to smuggle a deletion into a protected location.
#
# NOTE: the user's home directory (which is /root when running as
# real root with no SUDO_USER) is deliberately NOT in this list — it
# is protected separately, as an exact match only, in
# _is_protected_path() below. If "/root" were listed here with
# prefix-matching, it would block cleaning ~/.cache, ~/.config, etc.
# for a real-root session, defeating the User Cache Sweeper feature.
#
# This is the actual implementation backing the "Built-in Safety"
# claims in README.md — see that file for the user-facing description.
_PROTECTED_PREFIXES: tuple[str, ...] = (
    "/etc", "/usr", "/bin", "/sbin",
    "/lib", "/lib32", "/lib64",
    "/boot", "/proc", "/sys", "/dev",
)


def _is_protected_path(path: Path) -> bool:
    """True if `path` (after resolving symlinks) is a critical OS
    directory or the user's own home directory.

    Only meant to guard deletion of REAL files/directories. Deleting a
    symlink itself never touches whatever it points to, so callers
    should skip this check when the target being removed is a
    symlink (see delete_path_content below).
    """
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    resolved_str = str(resolved)

    if resolved_str == str(get_user_home()):
        return True

    return any(
        resolved_str == prefix or resolved_str.startswith(prefix + "/")
        for prefix in _PROTECTED_PREFIXES
    )

def _apt_env() -> dict:
    """Copy of the current environment with the locale forced to C.

    apt/dpkg translate their output based on the system locale, so
    code that matches literal English phrases in that output (e.g.
    "Reverse Depends:") silently gets nothing on a non-English
    system. Passing this env to subprocess calls forces English
    output regardless of the user's configured locale.
    """
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    return env

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


def _perform_single_delete(path: Path, sudo: bool) -> bool:
    """Delete one filesystem entry (file, symlink, or directory),
    applying the protected-path check and Dry Run reporting in the
    correct order: protection is checked FIRST, so Dry Run output
    accurately shows [BLOCKED] for protected paths instead of
    claiming they'd be deleted.
    """
    is_link = path.is_symlink()
    if not is_link and _is_protected_path(path):
        center_print(f"    {RED}[BLOCKED] Refusing to delete protected path: {path}{RESET}")
        return False

    if state.IS_DRY_RUN:
        kind = "symlink" if is_link else ("file" if path.is_file() else "directory")
        center_print(f"    {DIM}[DRY RUN] Would delete {kind}: {path}{RESET}")
        return True

    if is_link or path.is_file():
        if sudo: return _run(['rm', '-f', str(path)], use_sudo=True)
        path.unlink(); return True
    else:
        if sudo: return _run(['rm', '-rf', str(path)], use_sudo=True)
        shutil.rmtree(path, ignore_errors=True); return True


def delete_path_content(path: Path, delete_root: bool = False) -> bool:
    # NOTE: `path.exists()` follows symlinks, so it returns False for a
    # BROKEN symlink (one whose target is missing) even though the
    # symlink itself is still there on disk. Without the extra
    # `or path.is_symlink()` check, this function would silently no-op
    # on every broken symlink passed to it — which is exactly the
    # "Broken System Symlinks" cleanup feature's main use case. This
    # was a pre-existing bug in the original single-file version,
    # discovered while testing the protected-path fix below.
    if not path.exists() and not path.is_symlink():
        return True
    sudo = False if state.IS_DRY_RUN else check_sudo_status()
    try:
        if path.is_file() or path.is_symlink():
            return _perform_single_delete(path, sudo)
        if delete_root:
            return _perform_single_delete(path, sudo)
        ok = True
        for child in path.iterdir():
            try:
                ok &= _perform_single_delete(child, sudo)
            except OSError:
                ok = False
        return ok
    except PermissionError:
        return False


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
