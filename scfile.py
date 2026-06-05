import os
import sys
import subprocess
import shutil
import time
import re
from contextlib import contextmanager
from pathlib import Path


GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

HAS_SUDO_PERM: bool = False


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


def ask_choice() -> str:
    _flush_stdin()
    try:
        c = cols()
        return input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
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
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def delete_path_content(path: Path, delete_root: bool = False) -> bool:
    if not path.exists(): return True
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
        {"label": "General Application Cache", "path": str(home / ".cache"), "desc": "Temporary files for installed software including Pip.", "is_important": False},
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
    center_print(f"{RED}  [!] WARNING: Purge is PERMANENT. Files will NOT go to Trash.{RESET}")
    if ask_yes_no(f"{YELLOW}  [?] Wipe all listed profile caches?{RESET}"):
        print(); center_print(f"{CYAN}  [*] Erasing files...{RESET}")
        for r in results:
            if r["exists"]:
                targets = r["path"] if r.get("is_list") else [r["path"]]
                for t in targets: delete_path_content(Path(t), delete_root=r.get("is_list", False))
                center_print(f"    [{GREEN}✓{RESET}]  {r['label']}")
        print(); center_print(f"{GREEN}  [✓] Done: User profile scrubbed successfully.{RESET}")
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
    center_print(f"{RED}  [!] WARNING: Purge is PERMANENT. System files will be lost.{RESET}")
    if not ask_yes_no(f"{YELLOW}  [?] Purge all listed systemic core engines and cache layouts?{RESET}"):
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
    print(); center_print(f"{GREEN}  [✓] Success: System structural caches purged successfully.{RESET}")
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
    if ask_yes_no(f"{YELLOW}  [?] Purge all listed orphaned dependencies?{RESET}"):
        print(); center_print(f"{CYAN}  [*] Executing systemic purge...{RESET}")
        if _run(['apt-get', 'autoremove', '-y'], True): center_print(f"{GREEN}  [✓] Success: System free of orphaned artifacts.{RESET}")
        else: center_print(f"{RED}  [✗] Failure: Purge routine encountered an error.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No packages were removed.{RESET}")
    wait_for_enter()


def manage_large_files() -> None:
    clear_screen(); header("Advanced Large File Radar")
    
    # Get user home as default
    home = get_user_home()
    
    center_print(f"{YELLOW}  [?] Enter minimum file size in MB (default: 100):{RESET}")
    c = cols()
    try:
        size_input = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
        min_size_mb = int(size_input) if size_input else 100
    except ValueError:
        min_size_mb = 100
        center_print(f"{RED}  [!] Invalid input. Using default 100MB.{RESET}")
        time.sleep(1)

    center_print(f"{YELLOW}  [?] Enter scan path (default: {home}):{RESET}")
    path_input = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
    scan_path = Path(path_input) if path_input else home
    
    if not scan_path.exists() or not scan_path.is_dir():
        center_print(f"{RED}  [!] Path does not exist or is not a directory. Using {home}.{RESET}")
        scan_path = home
        time.sleep(1.5)

    center_print(f"{CYAN}  [*] Scanning {scan_path} for files > {min_size_mb}MB...{RESET}\n")
    
    skip = {'.cache', '.local', '.git', 'venv', '.venv', 'node_modules'}
    found_files = []
    min_size_bytes = min_size_mb * 1024 * 1024

    try:
        for dirpath, dirnames, filenames in os.walk(scan_path):
            # Prune skipped directories
            dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith('.')]
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    if not fp.is_symlink():
                        sz = fp.stat().st_size
                        if sz > min_size_bytes:
                            found_files.append((fp, sz))
                except (OSError, PermissionError):
                    pass
    except Exception as e:
        center_print(f"{RED}  [!] Error during scan: {e}{RESET}")

    if not found_files:
        center_print(f"{GREEN}  [✓] No files larger than {min_size_mb}MB found in {scan_path}.{RESET}")
        wait_for_enter(); return

    found_files.sort(key=lambda x: x[1], reverse=True)
    display_count = min(len(found_files), 10)
    
    center_print(f"{YELLOW}  [!] Top {display_count} Heavy Consumers identified:{RESET}\n")
    for fp, size in found_files[:display_count]:
        center_print(f"    {RED}{format_size(size):<10}{RESET}  {DIM}{fp}{RESET}")
    
    print()
    center_print(f"{DIM}Found a total of {len(found_files)} files meeting the criteria.{RESET}")
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
    if ask_yes_no(f"{YELLOW}  [?] Permanently remove these disabled revisions?{RESET}"):
        print(); center_print(f"{CYAN}  [*] Removing revisions...{RESET}\n")
        for n, r in disabled:
            ok = _run(['snap', 'remove', n, f'--revision={r}'], True)
            status = f"{GREEN}✓" if ok else f"{RED}✗"
            center_print(f"    [{status}{RESET}]  {n} (rev {r})")
        print(); center_print(f"{GREEN}  [✓] Done: Old revisions removed.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No revisions were removed.{RESET}")
    wait_for_enter()


def main_menu() -> None:
    global HAS_SUDO_PERM
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
        center_print(f"{CYAN}  [+] Framework Status: {mode}  {DIM}|{RESET}  Privileges: {lock}{RESET}")
        print(); _divider(); print()
        center_print(f"  {GREEN}{BOLD}[1]{RESET}  Deep Scan & Purge: User Profile Cache")
        center_print(f"  {GREEN}{BOLD}[2]{RESET}  Integrated Purge: System Engine Cache  {lock}")
        center_print(f"  {GREEN}{BOLD}[3]{RESET}  Architectural Scrub: Remove Old Snap Revisions  {lock}")
        center_print(f"  {GREEN}{BOLD}[4]{RESET}  Discovery: Find & Purge Orphaned Packages  {lock}")
        center_print(f"  {GREEN}{BOLD}[5]{RESET}  Radar: Identify Top 5 Largest Home Files")
        if not HAS_SUDO_PERM:
            print(); center_print(f"  {DIM}[9]  Elevate Session to Sudo{RESET}")
        print(); _divider(); print()
        center_print(f"  {RED}{BOLD}[0]{RESET}  {DIM}Exit CleanX{RESET}")
        print()
        choice = ask_choice()
        if choice == "1": manage_user_cache()
        elif choice in ("2", "3", "4"):
            if not HAS_SUDO_PERM:
                print(); center_print(f"{YELLOW}  [!] Action blocked: Sudo privileges required.{RESET}")
                if ask_yes_no("  [?] Authenticate Sudo right now?"):
                    if not attempt_elevation(): continue
            if choice == "2": manage_system_cache()
            elif choice == "3": clean_snap_old_versions()
            elif choice == "4": manage_orphaned_packages()
        elif choice == "5": manage_large_files()
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
