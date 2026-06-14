import os
import sys
import subprocess
import shutil
import time
import re
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime


GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

HAS_SUDO_PERM: bool = False
IS_DRY_RUN: bool = False


@contextmanager
def _no_echo():
    if os.name != 'posix':
        yield
        return
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        new = termios.tcgetattr(fd)
        new[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _flush_stdin() -> None:
    if os.name == 'posix':
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass


def clear_screen() -> None:
    print("\033[H\033[2J\033[3J", end="", flush=True)


def cols() -> int:
    return shutil.get_terminal_size().columns


def center_print(text: str) -> None:
    c = cols()
    plain_text = re.sub(r'\033\[[0-9;]*m', '', text)
    padding = max(0, (c - len(plain_text)) // 2)
    print(" " * padding + text)


def wait_for_enter() -> None:
    _flush_stdin()
    print()
    center_print(f"{DIM}Press [Enter] to return to the main menu...{RESET}")
    with _no_echo():
        while True:
            try:
                ch = sys.stdin.read(1)
                if ch in ('\n', '\r'):
                    break
            except (KeyboardInterrupt, EOFError):
                break


def header(title: str) -> None:
    w   = min(cols(), 68)
    bar = "═" * w
    print()
    center_print(f"{CYAN}{BOLD}{bar}{RESET}")
    center_print(f"{BOLD}{WHITE}  {title}  {RESET}")
    center_print(f"{CYAN}{BOLD}{bar}{RESET}")
    print()


def _divider(char: str = "─", width: int = 0) -> None:
    w = width if width > 0 else min(cols(), 65)
    center_print(f"{DIM}{char * w}{RESET}")


def app_logo() -> None:
    columns = cols()
    logo_lines = [
        f"{CYAN} ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██╗  ██╗{RESET}",
        f"{CYAN}██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║╚██╗██╔╝{RESET}",
        f"{WHITE}██║     ██║     █████╗  ███████║██╔██╗ ██║ ╚███╔╝ {RESET}",
        f"{WHITE}██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║ ██╔██╗ {RESET}",
        f"{GREEN}╚██████╗███████╗███████╗██║  ██║██║ ╚████║██╔╝ ██╗{RESET}",
        f"{GREEN} ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝{RESET}",
    ]
    logo_width = 63
    print()
    if columns >= logo_width:
        for line in logo_lines:
            plain = re.sub(r'\033\[[0-9;]*m', '', line)
            padding = max(0, (columns - len(plain)) // 2)
            print(" " * padding + line)
        slogan_text = "High-Performance Cache Analytics & Deep Scrub for Ubuntu Systems"
        slogan_colored = f"{BOLD}{WHITE}{slogan_text}{RESET}"
        divider_colored = f"{YELLOW}{'─' * len(slogan_text)}{RESET}"
        print()
        plain_slogan_pad = max(0, (columns - len(slogan_text)) // 2)
        print(" " * plain_slogan_pad + slogan_colored)
        print(" " * plain_slogan_pad + divider_colored)
    else:
        center_print(f"{CYAN}{BOLD}╔═══ CleanX ═══╗{RESET}")
        center_print(f"{BOLD}{WHITE}Cache & Deep Scrub Tool{RESET}")
    print("\n")


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    hint = f"{DIM}(y/N){RESET}" if default_no else f"{DIM}(Y/n){RESET}"
    while True:
        _flush_stdin()
        try:
            print()
            center_print(f"{prompt}  {hint}")
            c = cols()
            raw = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False

        if raw in ('y', 'yes', '1'):
            return True
        if raw in ('n', 'no', '0'):
            return False
        if raw == '':
            return not default_no

        center_print(f"{RED}  [!] Please enter (y) to confirm or (n) to cancel.{RESET}")
        time.sleep(1.5)
        print("\033[A\r\033[K" * 4, end="", flush=True)


def ask_choice(options: list[str]) -> str:
    _flush_stdin()
    while True:
        try:
            c = cols()
            raw = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
            if raw in options:
                return raw
            center_print(f"{RED}  [!] Operational mismatch: '{raw}' is not valid.{RESET}")
            time.sleep(1.2)
            print("\033[A\r\033[K" * 2, end="", flush=True)
        except (KeyboardInterrupt, EOFError):
            return "0"


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
    if IS_DRY_RUN:
        center_print(f"    {DIM}[DRY RUN] Would execute: {' '.join(cmd)}{RESET}")
        return True
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def delete_path_content(path: Path, delete_root: bool = False) -> bool:
    if not path.exists(): return True
    if IS_DRY_RUN:
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


def get_user_home() -> Path:
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        try:
            import pwd
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except Exception:
            return Path(f"~{sudo_user}").expanduser()
    return Path.home()


def check_sudo_status() -> bool:
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0


def attempt_elevation(show_intro: bool = False) -> bool:
    global HAS_SUDO_PERM
    if show_intro:
        clear_screen(); app_logo()
        center_print(f"{CYAN}{BOLD}[+] Privilege Initialization{RESET}")
        print()
        center_print("  Sudo rights are required for deep system cleaning.")
        center_print("  Restricted mode is available without elevation.")
        print(); _divider()
    if show_intro and not ask_yes_no(f"{YELLOW}[?] Elevate session to Sudo now?{RESET}"):
        HAS_SUDO_PERM = False
        print(); center_print(f"{YELLOW}  [-] Restricted mode authorized. System pathways locked.{RESET}")
        time.sleep(2.0); return False
    print(); center_print(f"{CYAN}  [*] Interrogating privilege stack...{RESET}")
    try:
        result = subprocess.run(['sudo', '-v'], check=False)
        if result.returncode == 0:
            HAS_SUDO_PERM = True
            center_print(f"{GREEN}  [✓] Authentication successful. High-privilege mode active.{RESET}")
            time.sleep(1.5); return True
        else:
            HAS_SUDO_PERM = False
            center_print(f"{RED}  [✗] Authentication failed. Dropping back to User mode.{RESET}")
            time.sleep(2.0); return False
    except Exception: HAS_SUDO_PERM = False; return False


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
        else: # Generic file search (like broken symlinks)
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


def manage_user_cache() -> None:
    clear_screen(); header("User Cache Sweeper")
    home = get_user_home()
    targets = [
        {"label": "Node Package Manager (npm)", "path": str(home / ".npm"), "desc": "Download cache for Javascript development libraries.", "is_important": False},
        {"label": "User Temporary Staging", "path": str(home / "tmp"), "desc": "Personal temporary folder for miscellaneous user data.", "is_important": False},
        {"label": "Snap Execution Cache", "path": str(home / "snap/common/.cache"), "desc": "Cached assets specifically for Snap package operations.", "is_important": True},
        {"label": "Command History Log", "path": str(home / ".bash_history"), "desc": "Stored history of your terminal execution commands.", "is_important": False},
        {"label": "System Trash Bin", "path": str(home / ".local/share/Trash"), "desc": "Contents currently residing in your Recycle Bin.", "is_important": False},
        {"label": "VS Code Interface Cache", "path": str(home / ".config/Code/Cache"), "desc": "Temporary Electron UI files for Visual Studio Code.", "is_important": False},
        {"label": "VS Code Script Cache", "path": str(home / ".config/Code/CachedData"), "desc": "Compiled script versions for faster VS Code launch.", "is_important": False},
        {"label": "VS Code Extension Cache", "path": str(home / ".vscode/extensions/.cache"), "desc": "Metadata and cached assets for your IDE plugins.", "is_important": False},
        {"label": "Firefox Web Cache", "path": str(home / ".cache/mozilla/firefox"), "desc": "Stored website snapshots and assets from Firefox.", "is_important": False},
        {"label": "Chrome Web Cache", "path": str(home / ".cache/google-chrome"), "desc": "Stored website snapshots and assets from Chrome.", "is_important": False},
        {"label": "Brave Web Cache", "path": str(home / ".cache/BraveSoftware/Brave-Browser"), "desc": "Stored website snapshots and assets from Brave.", "is_important": False},
    ]
    center_print(f"{CYAN}  [*] Initiating comprehensive user profile scan...{RESET}\n")
    results = scan_described_paths(targets)
    pyc_paths, pyc_size = _find_recursive_targets(home, "__pycache__")
    results.append({"label": "Python Bytecode Junk", "path": pyc_paths, "desc": "Recursive __pycache__ clusters found in your project folders.", "is_important": False, "exists": bool(pyc_paths), "size_bytes": pyc_size, "size_fmt": format_size(pyc_size), "is_list": True})
    dead_links, _ = _find_recursive_targets(home, "broken_symlinks")
    results.append({"label": "Broken System Symlinks", "path": dead_links, "desc": "Dead shortcuts pointing to non-existent file locations.", "is_important": True, "exists": bool(dead_links), "size_bytes": 0, "size_fmt": f"{len(dead_links)} links", "is_list": True})
    total = print_described_table(results, title=f"Target Profile: {CYAN}{home}{RESET}")
    if total == 0 and not any(r["label"] == "Broken System Symlinks" and r["exists"] for r in results):
        center_print(f"{GREEN}  [✓] Clean: No cache clutter detected.{RESET}"); wait_for_enter(); return
    
    if IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No files will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. Files will NOT go to Trash.{RESET}")
    
    prompt = "Wipe all listed profile caches?" if not IS_DRY_RUN else "Simulate profile cache wipe?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Erasing' if not IS_DRY_RUN else 'Simulating erasure of'} files...{RESET}")
        for r in results:
            if r["exists"]:
                targets = r["path"] if r.get("is_list") else [r["path"]]
                for t in targets: delete_path_content(Path(t), delete_root=r.get("is_list", False))
                center_print(f"    [{GREEN}✓{RESET}]  {r['label']}")
        msg = "User profile scrubbed successfully." if not IS_DRY_RUN else "Dry run complete. No files were removed."
        print(); center_print(f"{GREEN}  [✓] Done: {msg}{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No data was removed.{RESET}")
    wait_for_enter()


def manage_system_cache() -> None:
    clear_screen(); header("System Cache Sweeper")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: This option requires Sudo privileges.{RESET}"); wait_for_enter(); return
    targets = [
        {"label": "APT Package Archives", "path": "/var/cache/apt/archives", "desc": "Local repository of downloaded .deb installer files.", "is_important": True},
        {"label": "Systemd Crash Core Dumps", "path": "/var/lib/systemd/coredump", "desc": "Massive frozen snapshots of crashed applications.", "is_important": True},
        {"label": "Manual Page Cache", "path": "/var/cache/man", "desc": "Pre-rendered manual pages for system documentation.", "is_important": False},
        {"label": "Apache2 Server Cache", "path": "/var/cache/apache2", "desc": "Temporary web server assets and module caches.", "is_important": False},
        {"label": "App Store Info Cache", "path": "/var/cache/app-info", "desc": "Ubuntu Software metadata and catalog icons.", "is_important": False},
        {"label": "Software Catalog Cache", "path": "/var/cache/swcatalog", "desc": "AppStream software metadata for Linux repositories.", "is_important": False},
        {"label": "Temporary Files (/tmp)", "path": "/tmp", "desc": "System-wide temporary directory for all root processes.", "is_important": True},
    ]
    center_print(f"{CYAN}  [*] Scanning architectural system cache paths...{RESET}\n")
    results = scan_described_paths(targets)
    dead_logs, logs_size = _find_dead_logs(Path("/var/log"))
    results.append({"label": "Archived System Logs", "path": dead_logs, "desc": "Old versions of system logs (.gz and .old) no longer in use.", "is_important": False, "exists": bool(dead_logs), "size_bytes": logs_size, "size_fmt": format_size(logs_size), "is_list": True})
    total = print_described_table(results)
    if total == 0:
        center_print(f"{GREEN}  [✓] Clean: System engine caches are empty.{RESET}"); wait_for_enter(); return
    
    if IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No system files will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. System files will be lost.{RESET}")
    
    prompt = "Purge all listed systemic core engines and cache layouts?" if not IS_DRY_RUN else "Simulate systemic purge?"
    if not ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{YELLOW}  [-] Aborted: Core systemic architecture preserved safely.{RESET}"); wait_for_enter(); return
    print(); center_print(f"{CYAN}  [1/2] Pruning systemic package databases...{RESET}")
    _run(['apt-get', 'clean'], True); _run(['apt-get', 'autoremove', '-y'], True)
    center_print(f"    [{GREEN}✓{RESET}]  APT cleanup complete")
    center_print(f"{CYAN}  [2/2] Executing deep deployment scrub routines...{RESET}")
    for r in results:
        if r["exists"] and "APT" not in r["label"]:
            targets = r["path"] if r.get("is_list") else [r["path"]]
            for t in targets: delete_path_content(Path(t), delete_root=False)
            center_print(f"    [{GREEN}✓{RESET}]  {r['label']}")
    
    msg = "System structural caches purged successfully." if not IS_DRY_RUN else "Dry run complete. No system files were removed."
    print(); center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
    wait_for_enter()


def manage_orphaned_packages() -> None:
    clear_screen(); header("Orphaned Package Discovery")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}"); wait_for_enter(); return
    center_print(f"{CYAN}  [*] Querying APT for redundant dependencies...{RESET}\n")
    try:
        out = subprocess.check_output(["sudo", "apt-get", "autoremove", "--dry-run"], text=True)
    except Exception: out = ""
    orphans = []
    capture = False
    for line in out.splitlines():
        if "The following packages will be REMOVED:" in line: capture = True; continue
        if capture:
            if line.startswith(" ") or line.strip() == "":
                pkgs = line.strip().split()
                if pkgs: orphans.extend(pkgs)
            else: break
    if not orphans:
        center_print(f"{GREEN}  [✓] No orphaned packages identified.{RESET}"); wait_for_enter(); return
    center_print(f"{YELLOW}  [!] Identified {len(orphans)} orphaned packages:{RESET}\n")
    for pkg in sorted(orphans): center_print(f"    {DIM}→{RESET}  {pkg}")
    print()
    
    prompt = "Purge all listed orphaned dependencies?" if not IS_DRY_RUN else "Simulate orphaned package purge?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] Executing systemic purge...{RESET}")
        if _run(['apt-get', 'autoremove', '-y'], True): 
            msg = "System free of orphaned artifacts." if not IS_DRY_RUN else "Dry run complete. No packages were removed."
            center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
        else: center_print(f"{RED}  [✗] Failure: Purge routine encountered an error.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No packages were removed.{RESET}")
    wait_for_enter()


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
                time.sleep(1.2); print("\033[A\r\033[K" * 4, end="", flush=True); continue
            break
        except KeyboardInterrupt: print(); return
        except (ValueError, EOFError):
            center_print(f"{RED}  [!] Please enter a valid size (e.g., 100MB, 1.5GB).{RESET}")
            time.sleep(1.2); print("\033[A\r\033[K" * 4, end="", flush=True)

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
            time.sleep(1.2); print("\033[A\r\033[K" * 4, end="", flush=True)

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
        time.sleep(1.2); print("\033[A\r\033[K" * 4, end="", flush=True)

    age_str = f" and > {min_age_days} days old" if min_age_days > 0 else ""
    center_print(f"{CYAN}  [*] Scanning {scan_path} for files > {format_size(min_size_bytes)}{age_str}...{RESET}\n")
    
    abs_path = scan_path.expanduser().resolve()
    is_system_path = any(str(abs_path).startswith(p) for p in ['/var', '/root', '/etc', '/boot', '/usr'])
    if is_system_path and not HAS_SUDO_PERM:
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


def clean_snap_old_versions() -> None:
    clear_screen(); header("Snap Version Scrubber")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}"); wait_for_enter(); return
    center_print(f"{CYAN}  [*] Searching for disabled Snap revisions...{RESET}\n")
    try: out = subprocess.check_output(["snap", "list", "--all"], text=True)
    except Exception: out = ""
    disabled = []
    for line in out.splitlines()[1:]:
        if re.search(r'\bdisabled\b', line, re.IGNORECASE):
            parts = re.split(r'\s{2,}', line.strip())
            if not parts: parts = line.split()
            if len(parts) >= 3:
                name = parts[0]; rev = parts[2]
                if not rev.isdigit() and len(parts) > 3: rev = parts[3]
                disabled.append((name, rev))
    if not disabled:
        center_print(f"{GREEN}  [✓] No old Snap revisions found.{RESET}"); wait_for_enter(); return
    for name, rev in disabled: center_print(f"  {DIM}→{RESET}  {name:<28}  {DIM}[rev: {rev}]{RESET}")
    print()
    
    prompt = "Permanently remove these disabled revisions?" if not IS_DRY_RUN else "Simulate Snap revision removal?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Removing' if not IS_DRY_RUN else 'Simulating removal of'} revisions...{RESET}\n")
        for n, r in disabled:
            ok = _run(['snap', 'remove', n, f'--revision={r}'], True)
            status = f"{GREEN}✓" if ok else f"{RED}✗"
            center_print(f"    [{status}{RESET}]  {n} (rev {r})")
        msg = "Old revisions removed." if not IS_DRY_RUN else "Dry run complete. No Snaps were modified."
        print(); center_print(f"{GREEN}  [✓] Done: {msg}{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No revisions were removed.{RESET}")
    wait_for_enter()


def manage_journal_logs() -> None:
    clear_screen(); header("Journalctl Log Vacuum")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}"); wait_for_enter(); return

    center_print(f"{CYAN}  [*] Calculating current journal size...{RESET}")
    try:
        out = subprocess.check_output(["sudo", "journalctl", "--disk-usage"], text=True)
        center_print(f"  {YELLOW}{out.strip()}{RESET}")
    except Exception: pass
    print()

    center_print(f"{WHITE}{BOLD}[HOW IT WORKS:]{RESET}")
    center_print(f"  {DIM}●{RESET} {BOLD}Vacuum by Time:{RESET} Keeps recent logs and erases the old ones.")
    center_print(f"    {DIM}(Example: '2days' keeps only the last 48 hours of history){RESET}")
    center_print(f"  {DIM}●{RESET} {BOLD}Vacuum by Size:{RESET} Sets a maximum 'budget' for log files.")
    center_print(f"    {DIM}(Example: '200M' deletes logs until only 200MB remains){RESET}")
    print(); _divider(); print()

    center_print(f"  {GREEN}{BOLD}[1]{RESET}  Vacuum by Time")
    center_print(f"  {GREEN}{BOLD}[2]{RESET}  Vacuum by Size")
    center_print(f"  {RED}{BOLD}[0]{RESET}  Cancel")
    print()

    choice = ask_choice(["0", "1", "2"])
    if choice == "0": return

    if choice == "1":
        center_print(f"{YELLOW}  [?] Enter time limit (e.g., 2days, 1weeks):{RESET}")
        limit = input(" " * max(0, cols() // 2 - 3) + "  ➜  ").strip()
        if not limit: limit = "3days"
        cmd = ["journalctl", f"--vacuum-time={limit}"]
    else:
        center_print(f"{YELLOW}  [?] Enter size limit (e.g., 500M, 1G):{RESET}")
        limit = input(" " * max(0, cols() // 2 - 3) + "  ➜  ").strip()
        if not limit: limit = "500M"
        cmd = ["journalctl", f"--vacuum-size={limit}"]

    if IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No log entries will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. Log entries will be lost.{RESET}")
    
    prompt = f"Execute vacuum with limit '{limit}'?" if not IS_DRY_RUN else "Simulate journal vacuum?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Vacuuming' if not IS_DRY_RUN else 'Simulating vacuum of'} journal logs...{RESET}")
        if _run(cmd, True):
            msg = "Journal logs vacuumed successfully." if not IS_DRY_RUN else "Dry run complete. No logs were removed."
            center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
        else:
            center_print(f"{RED}  [✗] Failure: Vacuum routine encountered an error.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: Logs preserved.{RESET}")
    wait_for_enter()


def show_dry_run_help() -> None:
    clear_screen(); header("About Dry Run Mode")
    center_print(f"{CYAN}{BOLD}[WHAT IS IT?]{RESET}")
    center_print("  Dry Run is a safety simulation mode.")
    center_print("  It allows you to test the script without risk.")
    print()
    center_print(f"{YELLOW}{BOLD}[HOW IT WORKS:]{RESET}")
    center_print(f"  {GREEN}●{RESET} {BOLD}No Deletions:{RESET} Files are NOT erased from disk.")
    center_print(f"  {GREEN}●{RESET} {BOLD}No Changes:{RESET} System commands are NOT executed.")
    center_print(f"  {GREEN}●{RESET} {BOLD}Reporting:{RESET} It shows you exactly what WOULD happen.")
    print()
    center_print(f"{WHITE}{BOLD}[BENEFITS:]{RESET}")
    center_print("  1. Safely audit how much space you can reclaim.")
    center_print("  2. Verify that the file filters are working correctly.")
    center_print("  3. 100% peace of mind for new users.")
    print()
    _divider()
    center_print(f"{DIM}Press [9] on the main menu to toggle this mode on/off.{RESET}")
    wait_for_enter()



_CRITICAL_PACKAGES: set[str] = {
    "linux-base", "linux-image", "linux-headers", "grub", "grub2",
    "grub-common", "grub-pc", "grub-efi", "systemd", "systemd-sysv",
    "init", "udev", "dbus", "libc6", "libc-bin", "apt", "dpkg",
    "bash", "coreutils", "util-linux", "mount", "sudo", "passwd",
    "login", "adduser", "base-files", "base-passwd", "sysvinit-utils",
    "python3", "python3-minimal", "libpython3", "network-manager",
    "ifupdown", "iproute2", "openssh-server", "openssh-client",
    "gnome-shell", "ubuntu-desktop", "xorg", "xserver-xorg",
}


def _detect_package_manager(pkg: str) -> str | None:
    """
    Returns the package manager that owns the package:
    'apt', 'snap', 'flatpak', or None if not found.

    For flatpak: pkg may be a full app-ID (e.g. com.mitchellh.micro)
    or a short name (e.g. micro). We match against the last dotted
    component so both forms are recognised correctly.
    """
    try:
        r = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and "install ok installed" in r.stdout:
            return "apt"
    except Exception:
        pass

    try:
        r = subprocess.run(["snap", "list", pkg], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and pkg in r.stdout:
            return "snap"
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            pkg_lower = pkg.lower()
            for line in r.stdout.splitlines():
                app_id = line.strip()
                if not app_id:
                    continue
                short = app_id.split(".")[-1].lower()
                if app_id.lower() == pkg_lower or short == pkg_lower:
                    return "flatpak"
    except Exception:
        pass
    return None


def _get_apt_reverse_deps(pkg: str) -> list[str]:
    """
    Returns a list of installed packages that depend on `pkg`.
    Uses apt-cache rdepends + dpkg-query to filter only installed ones.
    """
    try:
        r = subprocess.run(
            ["apt-cache", "rdepends", "--installed", pkg],
            capture_output=True, text=True, timeout=15
        )
        deps: list[str] = []
        capture = False
        for line in r.stdout.splitlines():
            if line.strip() == "Reverse Depends:":
                capture = True
                continue
            if capture:
                dep = line.strip().lstrip("|").strip()
                if dep:
                    deps.append(dep)
        return list(set(deps))
    except Exception:
        return []


_PKG_ALIASES: dict[str, list[str]] = {
    "brave":            ["BraveSoftware", "brave", "brave-browser"],
    "brave-browser":    ["BraveSoftware", "brave", "brave-browser"],
    "google-chrome":    ["google-chrome", "google", "Google"],
    "chromium":         ["chromium", "chromium-browser"],
    "chromium-browser": ["chromium", "chromium-browser"],
    "firefox":          ["firefox", "mozilla", "Mozilla"],
    "thunderbird":      ["thunderbird", "Thunderbird", "mozilla"],
    "vlc":              ["vlc"],
    "gimp":             ["GIMP", "gimp"],
    "libreoffice":      ["libreoffice", "LibreOffice"],
    "vscode":           ["Code", "code", "vscode"],
    "code":             ["Code", "code", "vscode"],
    "discord":          ["discord", "Discord"],
    "slack":            ["Slack", "slack"],
    "spotify":          ["spotify", "Spotify"],
    "telegram-desktop": ["TelegramDesktop", "telegram-desktop"],
    "zoom":             ["zoom", "Zoom"],
    "obs-studio":       ["obs-studio", "obs"],
    "steam":            ["steam", "Steam"],
    "skype":            ["skypeforlinux", "Skype"],
}

def _collect_residuals(pkg: str, pm: str | None = None) -> list[dict]:
    """
    Builds a list of residual paths associated with `pkg`.
    Checks standard XDG dirs, Snap user data, known aliases, and
    performs a glob search in ~/.config / ~/.local/share for partial matches.

    For Flatpak: pkg is the full App ID (e.g. com.mitchellh.micro).
    The primary sandbox data lives at ~/.var/app/<AppID>/ and contains
    all user config/cache/data. We also derive the short name from the
    last dotted segment to search common XDG dirs.
    """
    home = get_user_home()

    if pm == "flatpak" and "." in pkg:
        short_name = pkg.split(".")[-1]
        search_names: list[str] = list(dict.fromkeys(
            [pkg, short_name]
            + _PKG_ALIASES.get(short_name, [])
            + _PKG_ALIASES.get(pkg, [])
        ))
    else:
        short_name = pkg
        search_names = list(dict.fromkeys([pkg] + _PKG_ALIASES.get(pkg, [])))

    raw_candidates: list[tuple[Path, str]] = []

    if pm == "flatpak":
        flatpak_var = home / ".var" / "app" / pkg
        raw_candidates.append((flatpak_var, f"Flatpak user data (~/.var/app/{pkg})"))

    for name in search_names:
        raw_candidates += [
            (home / ".config"      / name,  f"User config (~/.config/{name})"),
            (home / ".local/share" / name,  f"User data (~/.local/share/{name})"),
            (home / ".cache"       / name,  f"User cache (~/.cache/{name})"),
            (home / f".{name}",             f"Hidden home dir (~/.{name})"),
            (home / f".{name}rc",           f"RC dotfile (~/.{name}rc)"),
        ]

    raw_candidates.append((home / "snap" / pkg, f"Snap user data (~/snap/{pkg})"))

    glob_term = short_name.lower()
    for search_base, label_prefix, short_base in [
        (home / ".config",      "User config (glob)", "~/.config"),
        (home / ".local/share", "User data (glob)",   "~/.local/share"),
        (home / ".cache",       "User cache (glob)",  "~/.cache"),
    ]:
        try:
            if search_base.is_dir():
                for child in search_base.iterdir():
                    if re.search(r'\b' + re.escape(glob_term) + r'\b', child.name.lower()):
                        already = any(p == child for p, _ in raw_candidates)
                        if not already:
                            raw_candidates.append((child, f"{label_prefix} ({short_base}/{child.name})"))
        except PermissionError:
            pass

    seen: set[Path] = set()
    residuals: list[dict] = []
    for path, label in raw_candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.exists():
            continue
        size = _walk_size(path)
        residuals.append({
            "path":       path,
            "label":      label,
            "size_bytes": size,
            "size_fmt":   format_size(size),
            "exists":     True,
        })
    return residuals

def manage_memory_optimization() -> None:
      clear_screen(); header("Engine Optimization: RAM & Swap Reset")
      if not HAS_SUDO_PERM:
          center_print(f"{RED} [✗] Error: This operation requires Sudo privileges.{RESET}")
          wait_for_enter(); return

      center_print(f"{WHITE}{BOLD}[WHEN TO USE:]{RESET}")
      center_print(f"  {DIM}●{RESET} System feels sluggish or unresponsive")
      center_print(f"  {DIM}●{RESET} High RAM usage with cached data not releasing")
      center_print(f"  {DIM}●{RESET} Swap is full despite available RAM")
      center_print(f"  {DIM}●{RESET} After closing heavy applications (games, browsers, IDEs)")
      print(); _divider(); print()

      center_print(f"{CYAN}  [*] Current Memory Snapshot:{RESET}")
      subprocess.run(['free', '-h'])
      print()

      center_print(f"{WHITE}{BOLD}[PROCEDURE:]{RESET}")
      center_print(f"  {DIM}1.{RESET} Synchronize filesystem buffers (Safe-Write)")
      center_print(f"  {DIM}2.{RESET} Flush PageCache, Dentries, and Inodes")
      center_print(f"  {DIM}3.{RESET} Cycle Swap Architecture (Refresh slow memory)")
      print()

      if ask_yes_no(f"{YELLOW}  [?] Initiate memory optimization routine?{RESET}"):
          center_print(f"\n{CYAN}  [*] Synchronizing buffers...{RESET}")
          _run(['sync'], True)

          center_print(f"{CYAN}  [*] Flushing RAM cache layers...{RESET}")
          _run(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'], True)

          center_print(f"{CYAN}  [*] Cycling Swap (Moving data to RAM)...{RESET}")
          _run(['swapoff', '-a'], True)
          _run(['swapon', '-a'], True)

          center_print(f"\n{GREEN}  [✓] Optimization Complete.{RESET}")
          center_print(f"{CYAN}  [*] New Memory Snapshot:{RESET}")
          subprocess.run(['free', '-h'])
      else:
          center_print(f"\n{YELLOW}  [-] Optimization aborted.{RESET}")

      wait_for_enter()

def _search_packages(query: str) -> list[tuple[str, str]]:
    """Search all package managers for installed packages with names containing *query*.
    Returns a sorted list of (pm_name, package_name)."""
    results: list[tuple[str, str]] = []
    q = query.lower()

    try:
        r = subprocess.run(
            ["dpkg", "--get-selections"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 1 and parts[0].lower().startswith(q):
                if len(parts) < 2 or parts[1] == "install":
                    results.append(("apt", parts[0]))
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["snap", "list"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines()[1:]:
            name = line.split()[0] if line.split() else ""
            if name and name.lower().startswith(q):
                results.append(("snap", name))
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            app = line.strip()
            if app:
                short_name = app.split('.')[-1].lower()
                if app.lower().startswith(q) or short_name.startswith(q):
                    results.append(("flatpak", app))
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for pm, name in results:
        key = f"{pm}:{name}"
        if key not in seen:
            seen.add(key)
            unique.append((pm, name))
    return sorted(unique, key=lambda x: (x[1].lower(), x[0]))


def remove_program_and_residuals() -> None:
    """
    Interactive deep-removal tool.
    Detects the package manager, checks reverse dependencies, lists residuals,
    then removes both the program and its leftover files — safely.
    """
    clear_screen()
    header("Program Deep Removal & Residual Purge")

    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges are required for this operation.{RESET}")
        wait_for_enter()
        return

    while True:
        clear_screen(); header("Program Deep Removal & Residual Purge")
        center_print(f"{YELLOW}  [?] Enter the program name (or partial name) to remove (or press Enter to cancel):{RESET}")
        c = cols()
        try:
            raw = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if not raw:
            center_print(f"{YELLOW}  [-] Cancelled.{RESET}")
            wait_for_enter()
            return

        if not re.match(r'^[a-z0-9][a-z0-9+\-._]*$', raw):
            center_print(f"{RED}  [✗] Invalid input: '{raw}'. Aborting.{RESET}")
            time.sleep(2)
            continue

        if len(raw) < 3:
            center_print(f"{RED}  [✗] Please type at least 3 characters.{RESET}")
            time.sleep(2)
            continue

        candidates = _search_packages(raw)

        if not candidates:
            center_print(f"{RED}  [✗] No installed packages match '{raw}'.{RESET}")
            time.sleep(2)
            continue

        break

    if len(candidates) == 1:
        pkg = candidates[0][1]
        center_print(f"  {GREEN}[✓]{RESET}  Found: {BOLD}{pkg}{RESET}")
        print()
    else:
        center_print(f"{YELLOW}  [!] Multiple packages matching '{raw}':{RESET}\n")
        for i, (pm, name) in enumerate(candidates, 1):
            center_print(f"  {GREEN}{BOLD}[{i}]{RESET}  {name:<35}  {DIM}({pm.upper()}){RESET}")
        print()
        center_print(f"  {RED}{BOLD}[0]{RESET}  Cancel")
        print()
        choice = ask_choice([str(i) for i in range(len(candidates) + 1)])
        if choice == "0":
            center_print(f"{YELLOW}  [-] Cancelled.{RESET}")
            wait_for_enter()
            return
        pkg = candidates[int(choice) - 1][1]
        print()
        center_print(f"  {GREEN}[✓]{RESET}  Selected: {BOLD}{pkg}{RESET}")
        print()

    if pkg in _CRITICAL_PACKAGES or any(pkg.startswith(cp) for cp in _CRITICAL_PACKAGES):
        center_print(f"{RED}  [✗] BLOCKED: '{pkg}' is a critical system package.{RESET}")
        center_print(f"{RED}       Removing it could render your system unbootable.{RESET}")
        wait_for_enter()
        return

    print()
    center_print(f"{CYAN}  [*] Analyzing '{pkg}'...{RESET}")
    print()

    pm = _detect_package_manager(pkg)
    if pm is None:
        center_print(f"{YELLOW}  [!] '{pkg}' is not installed via APT, Snap, or Flatpak.{RESET}")
        center_print(f"{DIM}       Proceeding to scan for residual files only...{RESET}")
        print()
    else:
        center_print(f"  {GREEN}[✓]{RESET}  Found via {BOLD}{pm.upper()}{RESET}")
        print()

    critical_rdeps: list[str] = []
    normal_rdeps:   list[str] = []
    if pm == "apt":
        center_print(f"{CYAN}  [*] Checking reverse dependencies...{RESET}")
        rdeps = _get_apt_reverse_deps(pkg)
        if rdeps:
            for dep in rdeps:
                if dep in _CRITICAL_PACKAGES or any(dep.startswith(cp) for cp in _CRITICAL_PACKAGES):
                    critical_rdeps.append(dep)
                else:
                    normal_rdeps.append(dep)

        if critical_rdeps:
            print()
            center_print(f"{RED}{BOLD}  [✗] HARD BLOCK: Removing '{pkg}' will break CRITICAL system packages:{RESET}")
            for dep in critical_rdeps:
                center_print(f"      {RED}→  {dep}{RESET}")
            center_print(f"{RED}       Operation aborted to protect system integrity.{RESET}")
            wait_for_enter()
            return

        if normal_rdeps:
            print()
            center_print(f"{YELLOW}{BOLD}  [!] WARNING: The following installed packages depend on '{pkg}':{RESET}")
            for dep in normal_rdeps[:20]:
                center_print(f"      {YELLOW}→  {dep}{RESET}")
            if len(normal_rdeps) > 20:
                center_print(f"      {DIM}... and {len(normal_rdeps) - 20} more{RESET}")
            print()
            center_print(f"{YELLOW}  [!] These packages may break or be removed alongside '{pkg}'.{RESET}")
            print()
            if not ask_yes_no(f"{RED}  [?] Proceed despite dependent packages?{RESET}", default_no=True):
                print()
                center_print(f"{YELLOW}  [-] Aborted: No changes made.{RESET}")
                wait_for_enter()
                return
        else:
            center_print(f"  {GREEN}[✓]{RESET}  No reverse dependencies found. Safe to remove.")
        print()

    center_print(f"{CYAN}  [*] Scanning for residual files and directories...{RESET}")
    print()
    residuals = _collect_residuals(pkg, pm=pm)

    if residuals:
        center_print(f"{YELLOW}  [!] Residual footprint found:{RESET}\n")
        total_res = 0
        for r in residuals:
            center_print(f"  {DIM}→{RESET}  {r['label']:<45}  {YELLOW}{r['size_fmt']}{RESET}")
            total_res += r["size_bytes"]
        print()
        _divider()
        center_print(f"  Total residual size:  {YELLOW}{BOLD}{format_size(total_res)}{RESET}")
        print()
    else:
        center_print(f"  {GREEN}[✓]{RESET}  No residual files found.")
        print()

    if pm is None and not residuals:
        center_print(f"{GREEN}  [✓] Nothing to remove. System is already clean.{RESET}")
        wait_for_enter()
        return

    if IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No packages will be removed — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT.{RESET}")
    print()

    if pm is not None:
        prompt = f"Remove '{pkg}' via {pm.upper()} now?" if not IS_DRY_RUN else f"Simulate removal of '{pkg}'?"
        if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}", default_no=True):
            print()
            center_print(f"{CYAN}  [*] {'Removing' if not IS_DRY_RUN else 'Simulating removal of'} '{pkg}'...{RESET}\n")
            ok = False
            if pm == "apt":
                ok = _run(["apt-get", "purge", "-y", pkg], use_sudo=True)
                if ok:
                    _run(["apt-get", "autoremove", "-y"], use_sudo=True)
            elif pm == "snap":
                ok = _run(["snap", "remove", "--purge", pkg], use_sudo=True)
            elif pm == "flatpak":
                ok = _run(["flatpak", "uninstall", "-y", pkg], use_sudo=True)

            status = f"{GREEN}[✓]{RESET}" if ok else f"{RED}[✗]{RESET}"
            msg    = "removed successfully" if ok else "removal encountered an error"
            center_print(f"  {status}  '{pkg}' {msg}.")
            print()

            if residuals and ok:
                prompt_r = "Delete all residual files listed above?" if not IS_DRY_RUN else "Simulate residual deletion?"
                if ask_yes_no(f"{YELLOW}  [?] {prompt_r}{RESET}", default_no=True):
                    print()
                    center_print(f"{CYAN}  [*] {'Purging' if not IS_DRY_RUN else 'Simulating purge of'} residual files...{RESET}\n")
                    for r in residuals:
                        ok = delete_path_content(r["path"], delete_root=True)
                        status = f"{GREEN}✓" if ok else f"{RED}✗"
                        center_print(f"    [{status}{RESET}]  {r['label']}")
                    print()
                    msg = "Residuals purged." if not IS_DRY_RUN else "Dry run complete. No residuals were removed."
                    center_print(f"{GREEN}  [✓] {msg}{RESET}")
                else:
                    print()
        else:
            print()
            center_print(f"{YELLOW}  [-] Package removal skipped.{RESET}")
            print()
            center_print(f"{YELLOW}  [-] Residual files preserved.{RESET}")

    elif residuals:
        prompt_r = "Delete all residual files listed above?" if not IS_DRY_RUN else "Simulate residual deletion?"
        if ask_yes_no(f"{YELLOW}  [?] {prompt_r}{RESET}", default_no=True):
            print()
            center_print(f"{CYAN}  [*] {'Purging' if not IS_DRY_RUN else 'Simulating purge of'} residual files...{RESET}\n")
            for r in residuals:
                ok = delete_path_content(r["path"], delete_root=True)
                status = f"{GREEN}✓" if ok else f"{RED}✗"
                center_print(f"    [{status}{RESET}]  {r['label']}")
            print()
            msg = "Residuals purged." if not IS_DRY_RUN else "Dry run complete. No residuals were removed."
            center_print(f"{GREEN}  [✓] {msg}{RESET}")
        else:
            print()
            center_print(f"{YELLOW}  [-] Residual files preserved.{RESET}")

    wait_for_enter()


def main_menu() -> None:
    global HAS_SUDO_PERM
    global IS_DRY_RUN
    if check_sudo_status() or os.getuid() == 0:
        HAS_SUDO_PERM = True
        clear_screen(); app_logo()
        center_print(f"{GREEN}  [✓] Sudo authorization active.{RESET}")
        time.sleep(1.0)
    else: attempt_elevation(show_intro=True)

    while True:
        if not HAS_SUDO_PERM:
            if check_sudo_status(): HAS_SUDO_PERM = True
        else:
            if not check_sudo_status() and os.getuid() != 0: HAS_SUDO_PERM = False
        clear_screen(); app_logo()
        mode = f"{GREEN}{BOLD}Privileged{RESET}" if HAS_SUDO_PERM else f"{YELLOW}{BOLD}Restricted{RESET}"
        lock = f"{GREEN}[Unlocked]{RESET}" if HAS_SUDO_PERM else f"{RED}[Locked]{RESET}"
        dry  = f"{YELLOW}{BOLD}[DRY RUN ACTIVE]{RESET}" if IS_DRY_RUN else f"{DIM}[Real Mode]{RESET}"
        
        center_print(f"{CYAN}  [+] Framework Status: {mode}  {DIM}|{RESET}  Privileges: {lock}  {DIM}|{RESET}  Mode: {dry}")
        print(); _divider(); print()

        menu_width = min(cols() - 4, 68)
        indent = max(0, (cols() - menu_width) // 2)
        def m(text: str) -> None:
            plain = re.sub(r'\033\[[0-9;]*m', '', text)
            if len(plain) > menu_width:
                print(" " * indent + text)
            else:
                print(" " * indent + text + " " * max(0, menu_width - len(plain)))

        m(f"  {GREEN}{BOLD}[1]{RESET}  Deep Scan & Purge: User Profile Cache")
        m(f"  {GREEN}{BOLD}[2]{RESET}  Integrated Purge: System Engine Cache  {lock}")
        m(f"  {GREEN}{BOLD}[3]{RESET}  Architectural Scrub: Remove Old Snap Revisions  {lock}")
        m(f"  {GREEN}{BOLD}[4]{RESET}  Discovery: Find & Purge Orphaned Packages  {lock}")
        m(f"  {GREEN}{BOLD}[5]{RESET}  Radar: Advanced Deep Search for Large & Aged Files")
        m(f"  {GREEN}{BOLD}[6]{RESET}  Vacuum: Systemd Journal Logs (Log Cleanup)  {lock}")
        m(f"  {GREEN}{BOLD}[7]{RESET}  Deep Removal: Program + All Residual Files  {lock}")
        m(f"  {GREEN}{BOLD}[8]{RESET} Engine Optimization: RAM Cache & Swap Reset {lock}")

        dry_color = YELLOW if IS_DRY_RUN else DIM
        dry_label = "Disable" if IS_DRY_RUN else "Enable"
        print()
        m(f"  {dry_color}{BOLD}[9]{RESET}  {dry_label} Dry Run Mode (No deletion)")
        m(f"  {WHITE}{BOLD}[H]{RESET}  Help / About Dry Run Mode")

        if not HAS_SUDO_PERM:
            m(f"  {DIM}[10]  Elevate Session to Sudo{RESET}")
        print(); _divider(); print()
        m(f"  {RED}{BOLD}[0]{RESET}  {DIM}Exit CleanX{RESET}")
        print()
        valid = ["0", "1", "2", "3", "4", "5", "6", "7", "8","9", "H", "h"] + (["10"] if not HAS_SUDO_PERM else [])
        choice = ask_choice(valid)
        if choice == "1": manage_user_cache()
        elif choice in ("2", "3", "4", "6", "7", "8"):
            if not HAS_SUDO_PERM:
                print(); center_print(f"{YELLOW}  [!] Action blocked: Sudo privileges required.{RESET}")
                if ask_yes_no("  [?] Authenticate Sudo right now?"):
                    if not attempt_elevation(): continue
            if choice == "2": manage_system_cache()
            elif choice == "3": clean_snap_old_versions()
            elif choice == "4": manage_orphaned_packages()
            elif choice == "6": manage_journal_logs()
            elif choice == "7": remove_program_and_residuals()
            elif choice == "8": manage_memory_optimization()
        elif choice == "5": manage_large_files()
        elif choice == "9":
            IS_DRY_RUN = not IS_DRY_RUN
            center_print(f"{YELLOW}  [*] Dry Run Mode {'Enabled' if IS_DRY_RUN else 'Disabled'}.{RESET}")
            time.sleep(1.0)
        elif choice.upper() == "H":
            show_dry_run_help()
        elif choice == "10": attempt_elevation()
        elif choice == "0":
            print(); center_print(f"{GREEN}  [✓] Session terminated. Goodbye!{RESET}")
            sys.exit(0)
        else:
            print(); center_print(f"{RED}  [!] Operational mismatch: '{choice}' is not valid.{RESET}")
            time.sleep(1.5)
            print("\033[A\r\033[K" * 4, end="", flush=True)

if __name__ == "__main__":
    try: main_menu()
    except KeyboardInterrupt:
        print(); center_print(f"{RED}  [!] Operation interrupted.{RESET}")
        sys.exit(0)
