import os
import sys
import subprocess
import shutil
import time
import re
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta


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


def _divider(char: str = "─", width: int = 65) -> None:
    center_print(f"{DIM}{char * width}{RESET}")


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
    print()
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


def get_all_human_users() -> list[tuple[str, Path]]:
    users: list[tuple[str, Path]] = []
    try:
        with open("/etc/passwd") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) < 6: continue
                name, uid, home = parts[0], int(parts[2]), Path(parts[5].strip())
                if (uid == 0 or (uid >= 1000 and uid != 65534)) and home.is_dir():
                    users.append((name, home))
    except Exception: pass
    return sorted(users, key=lambda u: (u[0] != "root", u[0]))


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
    
    warning_mode = "PURGE IS PERMANENT" if not IS_DRY_RUN else "DRY RUN ACTIVE"
    center_print(f"{RED}  [!] WARNING: {warning_mode}. Files will NOT go to Trash.{RESET}")
    
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
    
    warning_mode = "PURGE IS PERMANENT" if not IS_DRY_RUN else "DRY RUN ACTIVE"
    center_print(f"{RED}  [!] WARNING: {warning_mode}. System files will be lost.{RESET}")
    
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
    
    # 1. Size Validation Loop
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

    # 2. Age Validation Loop
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

    # 3. Path Validation Loop
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

    # --- New Description Guide ---
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

    warning_mode = "PURGE IS PERMANENT" if not IS_DRY_RUN else "DRY RUN ACTIVE"
    center_print(f"{RED}  [!] WARNING: {warning_mode}. Log entries will be lost.{RESET}")
    
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
    center_print(f"{DIM}Press [8] on the main menu to toggle this mode on/off.{RESET}")
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
        center_print(f"  {GREEN}{BOLD}[1]{RESET}  Deep Scan & Purge: User Profile Cache")
        center_print(f"  {GREEN}{BOLD}[2]{RESET}  Integrated Purge: System Engine Cache  {lock}")
        center_print(f"  {GREEN}{BOLD}[3]{RESET}  Architectural Scrub: Remove Old Snap Revisions  {lock}")
        center_print(f"  {GREEN}{BOLD}[4]{RESET}  Discovery: Find & Purge Orphaned Packages  {lock}")
        center_print(f"  {GREEN}{BOLD}[5]{RESET}  Radar: Advanced Deep Search for Large & Aged Files")
        center_print(f"  {GREEN}{BOLD}[6]{RESET}  Vacuum: Systemd Journal Logs (Log Cleanup)  {lock}")
        
        dry_color = YELLOW if IS_DRY_RUN else DIM
        dry_label = "Disable" if IS_DRY_RUN else "Enable"
        print()
        center_print(f"  {dry_color}{BOLD}[8]{RESET}  {dry_label} Dry Run Mode (No deletion)")
        center_print(f"  {WHITE}{BOLD}[H]{RESET}  Help / About Dry Run Mode")
        
        if not HAS_SUDO_PERM:
            center_print(f"  {DIM}[9]  Elevate Session to Sudo{RESET}")
        print(); _divider(); print()
        center_print(f"  {RED}{BOLD}[0]{RESET}  {DIM}Exit CleanX{RESET}")
        print()
        valid = ["0", "1", "2", "3", "4", "5", "6", "8", "H", "h"] + (["9"] if not HAS_SUDO_PERM else [])
        choice = ask_choice(valid)
        if choice == "1": manage_user_cache()
        elif choice in ("2", "3", "4", "6"):
            if not HAS_SUDO_PERM:
                print(); center_print(f"{YELLOW}  [!] Action blocked: Sudo privileges required.{RESET}")
                if ask_yes_no("  [?] Authenticate Sudo right now?"):
                    if not attempt_elevation(): continue
            if choice == "2": manage_system_cache()
            elif choice == "3": clean_snap_old_versions()
            elif choice == "4": manage_orphaned_packages()
            elif choice == "6": manage_journal_logs()
        elif choice == "5": manage_large_files()
        elif choice == "8":
            IS_DRY_RUN = not IS_DRY_RUN
            center_print(f"{YELLOW}  [*] Dry Run Mode {'Enabled' if IS_DRY_RUN else 'Disabled'}.{RESET}")
            time.sleep(1.0)
        elif choice.upper() == "H":
            show_dry_run_help()
        elif choice == "9": attempt_elevation()
        elif choice == "0":
            print(); center_print(f"{GREEN}  [✓] Session terminated. Goodbye Nasser!{RESET}")
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
