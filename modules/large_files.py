"""Module [5]: Advanced Large & Aged File Radar."""
import re
import os
from datetime import datetime
from pathlib import Path

from core import state
from core.fs_utils import format_size
from core.sudo import get_user_home
from ui.colors import CYAN, YELLOW, RED, GREEN, DIM, RESET
from ui.terminal import clear_screen, header, center_print, cols, wait_for_enter


def manage_large_files() -> None:
    clear_screen(); header("Advanced Large & Aged File Radar")
    home = get_user_home()

    while True:
        center_print(f"{YELLOW}  [?] Enter minimum size (e.g., 500MB, 2GB, 1TB) [default: 100MB]:{RESET}")
        c = cols()
        try:
            size_input = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip().upper()
            if not size_input:
                min_size_bytes = 100 * 1024 * 1024
                break
            match = re.match(r"^(\d+\.?\d*)\s*([KMGT]B|[KMGT])?$", size_input)
            if not match: raise ValueError
            val = float(match.group(1))
            unit = match.group(2) if match.group(2) else "MB"
            multipliers = {"KB": 1024, "K": 1024, "MB": 1024**2, "M": 1024**2, "GB": 1024**3, "G": 1024**3, "TB": 1024**4, "T": 1024**4}
            min_size_bytes = int(val * multipliers.get(unit, 1024**2))
            if min_size_bytes > 10 * 1024**4:
                center_print(f"{RED}  [!] Input too large. Max limit is 10TB.{RESET}")
                time_sleep_and_clear()
                continue
            break
        except KeyboardInterrupt: print(); return
        except (ValueError, EOFError):
            center_print(f"{RED}  [!] Please enter a valid size (e.g., 100MB, 1.5GB).{RESET}")
            time_sleep_and_clear()

    while True:
        center_print(f"{YELLOW}  [?] Enter minimum age in days (press Enter to skip):{RESET}")
        c = cols()
        try:
            age_input = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
            if not age_input:
                min_age_days = 0
                break
            min_age_days = int(age_input)
            if min_age_days < 0: raise ValueError
            break
        except KeyboardInterrupt: print(); return
        except (ValueError, EOFError):
            center_print(f"{RED}  [!] Please enter a valid number of days.{RESET}")
            time_sleep_and_clear()

    while True:
        center_print(f"{YELLOW}  [?] Enter scan path (default: {home}):{RESET}")
        c = cols()
        try:
            path_input = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
            if not path_input:
                scan_path = home
                break
            p = Path(path_input).expanduser()
            if p.exists() and p.is_dir():
                scan_path = p
                break
            else:
                center_print(f"{RED}  [!] Path does not exist or is not a directory.{RESET}")
        except KeyboardInterrupt: print(); return
        except (EOFError):
            scan_path = home
            break
        time_sleep_and_clear()

    age_str = f" and > {min_age_days} days old" if min_age_days > 0 else ""
    center_print(f"{CYAN}  [*] Scanning {scan_path} for files > {format_size(min_size_bytes)}{age_str}...{RESET}\n")

    abs_path = scan_path.expanduser().resolve()
    is_system_path = any(str(abs_path).startswith(p) for p in ['/var', '/root', '/etc', '/boot', '/usr'])
    if is_system_path and not state.HAS_SUDO_PERM:
        center_print(f"{YELLOW}  [!] Scanning a system path without Sudo. Results may be incomplete.{RESET}\n")

    skip = {'.cache', '.local', '.git', 'venv', '.venv', 'node_modules', 'Downloads'}
    found_files = []
    skipped_dirs = 0
    now = datetime.now()

    def on_error(err: OSError):
        nonlocal skipped_dirs
        skipped_dirs += 1

    try:
        for dirpath, dirnames, filenames in os.walk(scan_path, onerror=on_error):
            dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith('.')]
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    if not fp.is_symlink():
                        stat = fp.stat()
                        sz = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        age_days = (now - mtime).days

                        if sz > min_size_bytes and age_days >= min_age_days:
                            found_files.append((fp, sz, age_days))
                except (OSError, PermissionError):
                    pass
    except Exception as e:
        center_print(f"{RED}  [!] Error during scan: {e}{RESET}")

    if not found_files:
        center_print(f"{GREEN}  [✓] No files matching the criteria found in {scan_path}.{RESET}")
        if skipped_dirs > 0:
            center_print(f"{DIM}      ({skipped_dirs} directories were skipped due to permissions){RESET}")
        wait_for_enter(); return

    found_files.sort(key=lambda x: x[1], reverse=True)
    display_count = min(len(found_files), 10)

    center_print(f"{YELLOW}  [!] Top {display_count} Heavy Consumers identified:{RESET}\n")
    for fp, size, age in found_files[:display_count]:
        age_label = f"{DIM}[{age}d old]{RESET}"
        center_print(f"    {RED}{format_size(size):<10}{RESET}  {age_label:<20}  {DIM}{fp}{RESET}")

    print()
    center_print(f"{DIM}Found a total of {len(found_files)} files meeting the criteria.{RESET}")
    if skipped_dirs > 0:
        center_print(f"{DIM}Notice: {skipped_dirs} directories were inaccessible and skipped.{RESET}")
    center_print(f"{DIM}Note: These files are not deleted automatically. Review them manually.{RESET}")
    wait_for_enter()


def time_sleep_and_clear() -> None:
    """Small shared helper for the repeated
    'sleep(1.2) then erase the last 4 printed lines' pattern used by
    the input-validation loops above."""
    import time
    time.sleep(1.2)
    print("\033[A\r\033[K" * 4, end="", flush=True)
