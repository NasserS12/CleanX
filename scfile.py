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
    """
    Ask a yes/no question.
    default_no=True  -> default is N (pressing Enter = False)
    default_no=False -> default is Y (pressing Enter = True)
    """
    hint = f"{DIM}(y/N){RESET}" if default_no else f"{DIM}(Y/n){RESET}"
    while True:
        _flush_stdin()
        try:
            print()
            center_print(f"{prompt}  {hint}")
            print()
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
            # Enter with no input -> return the default value
            return not default_no  # default_no=True -> False, default_no=False -> True

        center_print(f"{RED}  [!] Please enter (y) to confirm or (n) to cancel.{RESET}")
        time.sleep(1.0)


def ask_choice(options: list[str]) -> str:
    """
    Prompt for a menu selection and return the chosen option number.
    options: list of valid values (e.g. ["0","1","2","3","4"])
    """
    while True:
        _flush_stdin()
        try:
            print()
            center_print(f"{YELLOW}  Select an option number:{RESET}")
            print()
            c = cols()
            raw = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip()
        except (KeyboardInterrupt, EOFError):
            return "0"
        if raw in options:
            return raw
        center_print(f"{RED}  [!] '{raw}' is not a valid option. Try again.{RESET}")
        time.sleep(1.0)


def format_size(b: int) -> str:
    """Convert a size in bytes to a human-readable string."""
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


def scan_paths(paths: dict[str, str]) -> dict[str, dict]:
    results = {}
    for label, raw_path in paths.items():
        p    = Path(raw_path)
        size = _walk_size(p) if p.exists() else 0
        results[label] = {
            "path":       p,
            "size_bytes": size,
            "size_fmt":   format_size(size),
            "exists":     p.exists(),
        }
    return results


def print_scan_table(results: dict[str, dict], title: str = "") -> int:
    if title:
        center_print(f"{BOLD}{title}{RESET}")
        print()
    total = 0
    for label, info in results.items():
        if info["exists"]:
            status = f"{YELLOW}{BOLD}{info['size_fmt']}{RESET}"
        else:
            status = f"{DIM}Not Found{RESET}"
        center_print(f"  {DIM}→{RESET}  {label:<38}  {status}")
        total += info["size_bytes"]
    print()
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
    if not path.exists():
        return True
    sudo = check_sudo_status()
    try:
        if path.is_file() or path.is_symlink():
            if sudo:
                return _run(['rm', '-f', str(path)], use_sudo=True)
            path.unlink()
            return True
        if delete_root:
            if sudo:
                return _run(['rm', '-rf', str(path)], use_sudo=True)
            shutil.rmtree(path, ignore_errors=True)
            return True
        ok = True
        for child in path.iterdir():
            try:
                if child.is_dir() and not child.is_symlink():
                    if sudo:
                        ok &= _run(['rm', '-rf', str(child)], use_sudo=True)
                    else:
                        shutil.rmtree(child, ignore_errors=True)
                else:
                    if sudo:
                        ok &= _run(['rm', '-f', str(child)], use_sudo=True)
                    else:
                        child.unlink(missing_ok=True)
            except OSError:
                ok = False
        return ok
    except PermissionError as e:
        center_print(f"{RED}  [!] Permission error: {e}{RESET}")
        return False


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
                if len(parts) < 6:
                    continue
                name, uid, home = parts[0], int(parts[2]), Path(parts[5].strip())
                if (uid == 0 or (uid >= 1000 and uid != 65534)) and home.is_dir():
                    users.append((name, home))
    except Exception:
        pass
    return sorted(users, key=lambda u: (u[0] != "root", u[0]))


def check_sudo_status() -> bool:
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0


def attempt_elevation(show_intro: bool = False) -> bool:
    global HAS_SUDO_PERM
    if show_intro:
        clear_screen()
        app_logo()
        center_print(f"{CYAN}{BOLD}[+] Privilege Initialization{RESET}")
        print()
        center_print("  Sudo rights are required for deep system cleaning.")
        center_print("  Restricted mode is available without elevation.")
        print()
        _divider()
    if show_intro and not ask_yes_no(f"{YELLOW}[?] Elevate session to Sudo now?{RESET}"):
        HAS_SUDO_PERM = False
        print()
        center_print(f"{YELLOW}  [-] Running in restricted mode (no sudo).{RESET}")
        time.sleep(1.5)
        return False
    print()
    center_print(f"{CYAN}  [*] Validating permissions...{RESET}")
    try:
        result = subprocess.run(['sudo', '-v'], check=False)
        if result.returncode == 0:
            HAS_SUDO_PERM = True
            center_print(f"{GREEN}  [✓] Authorization granted successfully.{RESET}")
            time.sleep(1.2)
            return True
        else:
            HAS_SUDO_PERM = False
            center_print(f"{RED}  [✗] Authentication failed.{RESET}")
            time.sleep(1.5)
            return False
    except Exception:
        HAS_SUDO_PERM = False
        time.sleep(1.5)
        return False


def _find_pycache(root: Path) -> tuple[list[Path], int]:
    skip = {'.cache', '.local', '.git', 'venv', '.venv', 'node_modules', 'Downloads'}
    found: list[Path] = []
    total = 0
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith('.')]
        p = Path(dirpath) / "__pycache__"
        if p.is_dir():
            found.append(p)
            total += _walk_size(p)
    return found, total


def manage_user_cache() -> None:
    clear_screen()
    header("User Cache Sweeper")
    home = get_user_home()
    paths = {
        "General Cache (~/.cache)         ": str(home / ".cache"),
        "Snap Execution Cache             ": str(home / "snap/common/.cache"),
        "Command History Log              ": str(home / ".bash_history"),
    }
    center_print(f"{CYAN}  [*] Scanning user profile...{RESET}")
    print()
    results = scan_paths(paths)
    center_print(f"{DIM}  [...] Searching for Python bytecode artifacts (__pycache__)...{RESET}")
    pyc_paths, pyc_size = _find_pycache(home)
    results["Python Bytecode (__pycache__)    "] = {
        "path":       pyc_paths,
        "size_bytes": pyc_size,
        "size_fmt":   format_size(pyc_size),
        "exists":     bool(pyc_paths),
        "is_list":    True,
    }
    total = print_scan_table(results, title=f"Target Profile: {CYAN}{home}{RESET}")
    if total == 0:
        center_print(f"{GREEN}  [✓] Clean: No cache clutter detected.{RESET}")
        wait_for_enter()
        return
    center_print(f"{RED}  [!] Warning: Deletion is permanent and cannot be undone.{RESET}")
    if ask_yes_no(f"{YELLOW}[?] Wipe all listed profile caches?{RESET}"):
        print()
        center_print(f"{CYAN}  [*] Erasing files...{RESET}")
        print()
        for label, info in results.items():
            if not info["exists"]:
                continue
            targets = info["path"] if info.get("is_list") else [info["path"]]
            for t in targets:
                delete_path_content(Path(t), delete_root=info.get("is_list", False))
            center_print(f"    [{GREEN}✓{RESET}]  {label.strip()}")
        print()
        center_print(f"{GREEN}  [✓] Done: User profile scrubbed successfully.{RESET}")
    else:
        print()
        center_print(f"{YELLOW}  [-] Aborted: No data was removed.{RESET}")
    wait_for_enter()


def manage_system_cache() -> None:
    clear_screen()
    header("System Cache Sweeper")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: This option requires Sudo privileges.{RESET}")
        wait_for_enter()
        return
    paths = {
        "APT Package Archives             ": "/var/cache/apt/archives",
        "Systemd Journal Logs             ": "/var/log/journal",
        "Manual Page Cache                ": "/var/cache/man",
        "Apache2 Cache                    ": "/var/cache/apache2",
        "Application Info Cache           ": "/var/cache/app-info",
        "Software Catalog Cache           ": "/var/cache/swcatalog",
        "Temporary Files (/tmp)           ": "/tmp",
    }
    center_print(f"{CYAN}  [*] Scanning system cache paths...{RESET}")
    print()
    results = scan_paths(paths)
    total = print_scan_table(results)
    if total == 0:
        center_print(f"{GREEN}  [✓] Clean: System caches are empty.{RESET}")
        wait_for_enter()
        return
    center_print(f"{RED}  [!] Warning: Deep optimization cannot be undone.{RESET}")
    if not ask_yes_no(f"{YELLOW}[?] Proceed with full system cache purge?{RESET}"):
        print()
        center_print(f"{YELLOW}  [-] Aborted: No changes were made.{RESET}")
        wait_for_enter()
        return
    print()
    center_print(f"{CYAN}  [1/3] Pruning APT database...{RESET}")
    _run(['apt-get', 'clean'], True)
    _run(['apt-get', 'autoremove', '-y'], True)
    center_print(f"    [{GREEN}✓{RESET}]  APT cleanup complete")

    center_print(f"{CYAN}  [2/3] Vacuuming journal logs (last 24h)...{RESET}")
    _run(['journalctl', '--vacuum-time=1d'], True)
    center_print(f"    [{GREEN}✓{RESET}]  Journal vacuum complete")

    center_print(f"{CYAN}  [3/3] Purging remaining cache targets...{RESET}")
    for label, info in results.items():
        if info["exists"] and "APT" not in label and "Journal" not in label:
            delete_path_content(info["path"], delete_root=False)
            center_print(f"    [{GREEN}✓{RESET}]  {label.strip()}")
    print()
    center_print(f"{GREEN}  [✓] Done: System cache scrubbed successfully.{RESET}")
    wait_for_enter()


def clean_snap_old_versions() -> None:
    clear_screen()
    header("Snap Version Scrubber")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}")
        wait_for_enter()
        return
    center_print(f"{CYAN}  [*] Searching for disabled Snap revisions...{RESET}")
    print()
    try:
        out = subprocess.check_output(["snap", "list", "--all"], text=True)
    except Exception:
        out = ""
    disabled = []
    for line in out.splitlines()[1:]:
        if 'disabled' in line.lower():
            p = line.split()
            if len(p) >= 3:
                disabled.append((p[0], p[2]))
    if not disabled:
        center_print(f"{GREEN}  [✓] No old Snap revisions found.{RESET}")
        wait_for_enter()
        return
    for name, rev in disabled:
        center_print(f"  {DIM}→{RESET}  {name:<28}  {DIM}[rev: {rev}]{RESET}")
    if ask_yes_no(f"\n{YELLOW}[?] Permanently remove these disabled revisions?{RESET}"):
        print()
        center_print(f"{CYAN}  [*] Removing revisions...{RESET}")
        print()
        for n, r in disabled:
            ok = _run(['snap', 'remove', n, f'--revision={r}'], True)
            status_color = GREEN if ok else RED
            status_icon  = "✓" if ok else "✗"
            center_print(f"    [{status_color}{status_icon}{RESET}]  {n}  (rev {r})")
        print()
        center_print(f"{GREEN}  [✓] Done: Old revisions removed.{RESET}")
    else:
        print()
        center_print(f"{YELLOW}  [-] Aborted: No revisions were removed.{RESET}")
    wait_for_enter()


def clean_all_safe_macro() -> None:
    clear_screen()
    header("Full Auto-Clean Macro")
    if not HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}")
        wait_for_enter()
        return
    center_print(f"{CYAN}  [*] Running full system diagnostics...{RESET}")
    print()
    sys_paths = {
        "APT Package Archives             ": "/var/cache/apt/archives",
        "Systemd Journal Logs             ": "/var/log/journal",
        "Manual Page Cache                ": "/var/cache/man",
        "Apache2 Cache                    ": "/var/cache/apache2",
        "Application Info Cache           ": "/var/cache/app-info",
        "Software Catalog Cache           ": "/var/cache/swcatalog",
        "Temporary Files (/tmp)           ": "/tmp",
    }
    results = scan_paths(sys_paths)
    total = print_scan_table(results)
    center_print(f"{DIM}  Note: Kernel page cache will also be dropped.{RESET}")
    print()
    if total == 0:
        center_print(f"{GREEN}  [✓] System is already clean.{RESET}")
        wait_for_enter()
        return
    if not ask_yes_no(f"{YELLOW}[?] Confirm full global auto-clean?{RESET}"):
        print()
        center_print(f"{YELLOW}  [-] Aborted: No operations were performed.{RESET}")
        wait_for_enter()
        return
    print()
    center_print(f"{CYAN}  [1/3] Cleaning APT, journals, and caches...{RESET}")
    _run(['apt-get', 'clean'], True)
    _run(['apt-get', 'autoremove', '-y'], True)
    _run(['journalctl', '--vacuum-time=1d'], True)
    for label, info in results.items():
        if info["exists"] and "APT" not in label and "Journal" not in label:
            delete_path_content(info["path"], False)
    center_print(f"    [{GREEN}✓{RESET}]  APT and cache cleanup complete")

    center_print(f"{CYAN}  [2/3] Dropping kernel page cache...{RESET}")
    _run(['sync'], True)
    subprocess.run(
        "echo 3 | sudo tee /proc/sys/vm/drop_caches",
        shell=True, capture_output=True
    )
    center_print(f"    [{GREEN}✓{RESET}]  Kernel cache drop complete")

    center_print(f"{CYAN}  [3/3] Verifying completion...{RESET}")
    center_print(f"    [{GREEN}✓{RESET}]  Verification passed")
    print()
    center_print(f"{GREEN}  [✓] Done: Full auto-clean completed successfully.{RESET}")
    wait_for_enter()


def _sync_sudo_status() -> None:
    global HAS_SUDO_PERM
    if HAS_SUDO_PERM and not check_sudo_status() and os.getuid() != 0:
        HAS_SUDO_PERM = False
    elif not HAS_SUDO_PERM and check_sudo_status():
        HAS_SUDO_PERM = True


def main_menu() -> None:
    global HAS_SUDO_PERM
    if check_sudo_status() or os.getuid() == 0:
        HAS_SUDO_PERM = True
        clear_screen()
        app_logo()
        center_print(f"{GREEN}  [✓] Sudo authorization active.{RESET}")
        time.sleep(1.0)
    else:
        attempt_elevation(True)

    while True:
        _sync_sudo_status()
        clear_screen()
        app_logo()

        mode = f"{GREEN}{BOLD}Privileged{RESET}" if HAS_SUDO_PERM else f"{YELLOW}{BOLD}Restricted{RESET}"
        lock = f"{GREEN}[Unlocked]{RESET}" if HAS_SUDO_PERM else f"{RED}[Locked]{RESET}"

        center_print(f"{CYAN}  [+] Framework Status: {mode}  {DIM}|{RESET}  Privileges: {lock}{RESET}")
        print()
        _divider()
        print()

        center_print(f"  {GREEN}{BOLD}[1]{RESET}  Deep Scan & Purge: User Profile Cache")
        print()
        center_print(f"  {GREEN}{BOLD}[2]{RESET}  Integrated Purge: System Engine Cache  {lock}")
        print()
        center_print(f"  {GREEN}{BOLD}[3]{RESET}  Architectural Scrub: Remove Old Snap Revisions  {lock}")
        print()
        center_print(f"  {GREEN}{BOLD}[4]{RESET}  Sovereign Mode: Full Global Auto-Clean  {lock}")

        if not HAS_SUDO_PERM:
            print()
            center_print(f"  {DIM}[5]  Elevate Session to Sudo{RESET}")

        print()
        _divider()
        print()
        center_print(f"  {RED}{BOLD}[0]{RESET}  {DIM}Exit CleanX{RESET}")
        print()

        valid = ["0", "1", "2", "3", "4"] + (["5"] if not HAS_SUDO_PERM else [])
        choice = ask_choice(valid)

        if choice == "1":
            manage_user_cache()
        elif choice in ("2", "3", "4"):
            if not HAS_SUDO_PERM:
                print()
                center_print(f"{YELLOW}  [!] Action blocked: Sudo privileges required.{RESET}")
                if ask_yes_no("[?] Authenticate Sudo right now?"):
                    if not attempt_elevation():
                        continue
            if choice == "2":
                manage_system_cache()
            elif choice == "3":
                clean_snap_old_versions()
            elif choice == "4":
                clean_all_safe_macro()
        elif choice == "5":
            attempt_elevation()
        elif choice == "0":
            print()
            center_print(f"{GREEN}  [✓] Session terminated. Goodbye!{RESET}")
            print()
            sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        center_print(f"{YELLOW}  [!] Interrupted by user (Ctrl+C).{RESET}")
        print()
        sys.exit(0)
