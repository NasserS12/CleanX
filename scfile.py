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


def wait_for_enter() -> None:
    _flush_stdin()
    print(f"\n{DIM}  Press [Enter] to return to the main menu...{RESET}", end="", flush=True)
    with _no_echo():
        while True:
            try:
                ch = sys.stdin.read(1)
                if ch in ('\n', '\r'):
                    break
            except (KeyboardInterrupt, EOFError):
                break


def cols() -> int:
    return shutil.get_terminal_size().columns


def header(title: str) -> None:
    w   = min(cols(), 68)
    bar = "═" * w
    print(f"\n{CYAN}{bar.center(cols())}")
    print(f"{BOLD}{title.center(cols())}{RESET}")
    print(f"{CYAN}{bar.center(cols())}{RESET}\n")


def _divider(char: str = "─", width: int = 65) -> None:
    print(f"  {DIM}{char * width}{RESET}")


def app_logo():
    columns = shutil.get_terminal_size().columns
    
    logo_cleanx = [
        " ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██╗  ██╗",
        "██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║╚██╗██╔╝",
        "██║     ██║     █████╗  ███████║██╔██╗ ██║ ╚███╔╝ ",
        "██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║ ██╔██╗ ",
        "╚██████╗███████╗███████╗██║  ██║██║ ╚████║██╔╝ ██╗",
        " ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"
    ]
    
    print(f"\n{RED}")
    for line in logo_cleanx:
        print(line.center(columns))
    print(f"{RESET}")
    
    slogan  = " High-Performance Cache Analytics & Deep Scrub for Ubuntu Systems "
    padding_slogan = " " * max(0, (columns - len(slogan)) // 2)

    print(f"{padding_slogan}{YELLOW}{slogan}{RESET}\n\n\n")


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    hint = "(y/N)" if default_no else "(Y/n)"
    while True:
        _flush_stdin()
        try:
            raw = input(f"{prompt} {CYAN}{hint}{RESET}: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False

        if raw in ('y', 'yes', '1'):
            return True
        if raw in ('n', 'no', '0', ''):
            return default_no is False if raw == '' else False
        if raw == '' and default_no:
            return False

        print(f"  {RED}[!] Please enter (y) or (n) only.{RESET}", end="", flush=True)
        time.sleep(1.5)
        print("\r\033[K\033[A\r\033[K", end="", flush=True)


def ask_choice(options: list[str]) -> str:
    valid = [str(i) for i in range(len(options) + 1)]
    while True:
        _flush_stdin()
        try:
            raw = input(f"\n{YELLOW}  Select option number: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return "0"
        if raw in valid:
            return raw
        print(f"  {RED}[!] '{raw}' is invalid — please enter a valid option number.{RESET}",
              end="", flush=True)
        time.sleep(1.5)
        print("\r\033[K", end="", flush=True)


def format_size(b: int) -> str:
    if b <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} PB"


def _walk_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() and not path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    try:
        out = subprocess.run(
            ["du", "-sb", str(path)],
            capture_output=True, text=True, timeout=30
        )
        if out.returncode == 0:
            return int(out.stdout.split()[0])
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file() and not f.is_symlink():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except PermissionError:
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
        print(f"  {BOLD}{title}{RESET}\n")
    total = 0
    for label, info in results.items():
        if info["exists"]:
            status = f"{YELLOW}{info['size_fmt']}{RESET}"
        else:
            status = f"{DIM}Not Found{RESET}"
        print(f"  {DIM}→{RESET}  {label:<35}  {status}")
        total += info["size_bytes"]
    _divider()
    color = GREEN if total == 0 else YELLOW
    print(f"  Total footprint: {color}{BOLD}{format_size(total)}{RESET}\n")
    return total


def _run(cmd: list[str], use_sudo: bool = False) -> bool:
    if use_sudo and 'sudo' not in cmd:
        cmd = ['sudo'] + cmd
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
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
        print(f"  {RED}[!] Insufficient privileges: {e}{RESET}")
        return False


def get_user_home() -> Path:
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        try:
            import pwd
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except (KeyError, ImportError):
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
                name = parts[0]
                uid  = int(parts[2])
                home = Path(parts[5].strip())
                if (uid == 0 or (uid >= 1000 and uid != 65534)) and home.is_dir():
                    users.append((name, home))
    except OSError:
        pass
    return sorted(users, key=lambda u: (u[0] != "root", u[0]))


def check_sudo_status() -> bool:
    return subprocess.run(
        ['sudo', '-n', 'true'],
        capture_output=True
    ).returncode == 0


def attempt_elevation(show_intro: bool = False) -> bool:
    global HAS_SUDO_PERM

    if show_intro:
        clear_screen()
        app_logo()
        print(f"{CYAN}  [+] Privilege Initialization:{RESET}\n")
        print(f"  Sudo rights are required to clean structural systems (APT, Logs).")
        print(f"  You can still opt to proceed in unprivileged, restricted environment mode.")
        _divider()

    if show_intro and not ask_yes_no(f"\n  {YELLOW}[?] Elevate execution session context to Sudo now?{RESET}"):
        HAS_SUDO_PERM = False
        print(f"\n  {YELLOW}[-] Running session initialized in restricted mode.{RESET}")
        time.sleep(2.0)
        return False

    print(f"\n  {CYAN}[*] Validating session permissions context...{RESET}")
    try:
        result = subprocess.run(['sudo', '-v'], check=False)
        if result.returncode == 0:
            HAS_SUDO_PERM = True
            print(f"  {GREEN}[✓] Authorization successful. Sudo environment active.{RESET}")
            time.sleep(1.5)
            return True
        else:
            HAS_SUDO_PERM = False
            print(f"  {RED}[✗] Authentication failed. Dropping to restricted mode.{RESET}")
            time.sleep(2.0)
            return False
    except FileNotFoundError:
        HAS_SUDO_PERM = False
        print(f"  {RED}[✗] Binary execution mismatch: Sudo package is not installed.{RESET}")
        time.sleep(2.0)
        return False


def _find_pycache(root: Path) -> tuple[list[Path], int]:
    skip = {
        '.cache', '.local', '.git', 'venv', '.venv', 'node_modules',
        'Downloads', 'Pictures', 'Videos', 'Music', 'Desktop',
        '.cargo', '.rustup', '.npm', '.nvm', '.vscode', '.idea',
    }
    found: list[Path] = []
    total = 0
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        p = Path(dirpath) / "__pycache__"
        if p.is_dir():
            found.append(p)
            total += _walk_size(p)
    return found, total


def manage_user_cache() -> None:
    clear_screen()
    header("User Directory Cache Sweeper")
    home = get_user_home()

    paths_to_scan = {
        "General Cache (~/.cache)         ": str(home / ".cache"),
        "Local Temporary (~/.local/tmp)   ": str(home / ".local/tmp"),
        "Snap Execution Caches            ": str(home / "snap/common/.cache"),
        "Command History Log Target       ": str(home / ".bash_history"),
    }

    print(f"  {CYAN}[*] Evaluating profile scope pathways...{RESET}\n")
    results = scan_paths(paths_to_scan)

    print(f"  {DIM}[...] Searching for bytecode artifacts (__pycache__)...{RESET}", end="\r")
    pyc_paths, pyc_size = _find_pycache(home)
    sys.stdout.write("\033[K")
    results["Python Bytecode (__pycache__)    "] = {
        "path":       pyc_paths,
        "size_bytes": pyc_size,
        "size_fmt":   format_size(pyc_size),
        "exists":     bool(pyc_paths),
        "is_list":    True,
    }

    total = print_scan_table(results, title=f"Active Profile Target: {CYAN}{home}{RESET}")

    if not any(v["exists"] for v in results.values()):
        print(f"  {GREEN}[✓] Pristine state: Target profile directories have no layout clutter.{RESET}")
        wait_for_enter()
        return

    print(f"  {RED}[!] Warning: Data destruction is irreversible.{RESET}")
    if ask_yes_no(f"\n  {YELLOW}[?] Proceed with wiping all listed profile cache layers?{RESET}"):
        print(f"\n  {CYAN}[*] Erasing files...{RESET}")
        for label, info in results.items():
            if not info["exists"]:
                continue
            targets = info["path"] if info.get("is_list") else [info["path"]]
            delete_root = info.get("is_list", False)
            for t in (targets if isinstance(targets, list) else [targets]):
                ok = delete_path_content(Path(t), delete_root=delete_root)
                icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
                print(f"  [{icon}] {label.strip()}")
        print(f"\n  {GREEN}[✓] Success: Profile structures scrubbed efficiently.{RESET}")
    else:
        print(f"\n  {YELLOW}[-] Aborted: Profile scope context remains untouched.{RESET}")

    wait_for_enter()


def manage_system_cache() -> None:
    clear_screen()
    header("System Structural Cache Sweeper")

    if not HAS_SUDO_PERM:
        print(f"  {RED}[✗] Restricted: High privilege access block. Sudo authorization required.{RESET}")
        wait_for_enter()
        return

    paths_to_scan = {
        "APT Package Archives              ": "/var/cache/apt/archives",
        "Systemd Logging Journal Layouts   ": "/var/log/journal",
        "Global Volatile Directory (/tmp)  ": "/tmp",
    }

    print(f"  {CYAN}[*] Evaluating core engine directory arrays...{RESET}\n")
    results = scan_paths(paths_to_scan)
    total = print_scan_table(results)

    if total == 0:
        print(f"  {GREEN}[✓] Pristine state: Structural cache segments are empty.{RESET}")
        wait_for_enter()
        return

    print(f"  {RED}[!] Warning: Destructive system optimization cannot be rolled back.{RESET}")
    if not ask_yes_no(f"\n  {YELLOW}[?] Proceed with full system-wide core cache clean?{RESET}"):
        print(f"\n  {YELLOW}[-] Aborted: Core systemic infrastructure preserved.{RESET}")
        wait_for_enter()
        return

    print(f"\n  {CYAN}[1/3] Executing package database list prune (APT)...{RESET}")
    ok1 = _run(['apt-get', 'clean'], use_sudo=True)
    ok2 = _run(['apt-get', 'autoremove', '-y'], use_sudo=True)
    _print_step_result("APT clean + autoremove", ok1 and ok2)

    print(f"  {CYAN}[2/3] Compressing log frameworks (Vacuuming to 24h retention)...{RESET}")
    ok3 = _run(['journalctl', '--vacuum-time=1d'], use_sudo=True)
    _print_step_result("Journal vacuum routine", ok3)

    print(f"  {CYAN}[3/3] Purging obsolete volatile mounts (/tmp content)...{RESET}")
    ok4 = delete_path_content(Path("/tmp"), delete_root=False)
    _print_step_result("/tmp cleanup routine", ok4)

    print(f"\n  {GREEN}[✓] Success: Architectural core structural system caches purged.{RESET}")
    wait_for_enter()


def _print_step_result(label: str, ok: bool) -> None:
    icon  = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    state = f"{GREEN}Success{RESET}" if ok else f"{RED}Failure{RESET}"
    print(f"    [{icon}] {label}: {state}")


def _get_disabled_snaps() -> list[tuple[str, str]]:
    try:
        out = subprocess.check_output(["snap", "list", "--all"], text=True, timeout=15)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    disabled: list[tuple[str, str]] = []
    for line in out.splitlines()[1:]:
        if not re.search(r'\bdisabled\b', line, re.IGNORECASE):
            continue
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            rev  = parts[2]
            if not rev.isdigit() and len(parts) > 3:
                rev = parts[3]
            disabled.append((name, rev))
    return disabled


def clean_snap_old_versions() -> None:
    clear_screen()
    header("Superseded Snap Package Scrubber")

    if not HAS_SUDO_PERM:
        print(f"  {RED}[✗] Restricted: Snap configuration layers are locked. Sudo required.{RESET}")
        wait_for_enter()
        return

    print(f"  {CYAN}[*] Evaluating snap engine layout arrays...{RESET}\n")
    disabled = _get_disabled_snaps()

    if not disabled:
        print(f"  {GREEN}[✓] Clean: No legacy disabled snap revisions found on system.{RESET}")
        wait_for_enter()
        return

    print(f"  {YELLOW}[!] Detected {len(disabled)} obsolete packages available for deletion:{RESET}\n")
    for name, rev in disabled:
        print(f"    {DIM}→{RESET}  {name:<25} [revision: {rev}]")

    print(f"\n  {RED}[!] Warning: Purged package variations are permanent.{RESET}")
    if not ask_yes_no(f"\n  {YELLOW}[?] Proceed with structural snap array package purging?{RESET}"):
        print(f"\n  {YELLOW}[-] Aborted: App software packages preserved.{RESET}")
        wait_for_enter()
        return

    print(f"\n  {CYAN}[*] Wiping package configurations...{RESET}")
    for name, rev in disabled:
        ok = _run(['snap', 'remove', name, f'--revision={rev}'], use_sudo=True)
        _print_step_result(f"{name} rev.{rev}", ok)

    print(f"\n  {GREEN}[✓] Success: Superseded applications records dropped.{RESET}")
    wait_for_enter()


def clean_all_safe_macro() -> None:
    clear_screen()
    header("Sovereign Mode — Sovereign Automation Execution Grid")

    if not HAS_SUDO_PERM:
        print(f"  {RED}[✗] Access Denied: High-tier global routine requires Sudo integration.{RESET}")
        wait_for_enter()
        return

    print(f"  {CYAN}[*] Running general diagnostics framework...{RESET}\n")

    sys_paths = {
        "APT Package Archives              ": "/var/cache/apt/archives",
        "System Journal Logs               ": "/var/log/journal",
        "Temporary Files (/tmp)            ": "/tmp",
    }
    sys_results = scan_paths(sys_paths)

    thumb_total = 0
    thumb_paths: list[Path] = []
    for _, home in get_all_human_users():
        tp = home / ".cache" / "thumbnails"
        if tp.is_dir():
            thumb_paths.append(tp)
            thumb_total += _walk_size(tp)

    sys_results["Thumbnail Cache (all users)       "] = {
        "path":       thumb_paths,
        "size_bytes": thumb_total,
        "size_fmt":   format_size(thumb_total),
        "exists":     thumb_total > 0,
        "is_list":    True,
    }

    total = print_scan_table(sys_results, title="Global Storage Scrub Topology Summary")
    print(f"  {DIM}Note: Virtual memory optimization (drop caches) will append execution sequence.{RESET}\n")

    if total == 0:
        print(f"  {GREEN}[✓] Pristine state: Global infrastructure storage optimization is complete.{RESET}")
        wait_for_enter()
        return

    print(f"  {RED}[!] Danger: Sovereign optimization destroys all target tracking configurations permanently.{RESET}")
    if not ask_yes_no(f"\n  {YELLOW}[?] Authorize full global structural macro cleanup sequence?{RESET}"):
        print(f"\n  {YELLOW}[-] Aborted: Global automation framework sequence cancelled.{RESET}")
        wait_for_enter()
        return

    print()
    print(f"  {CYAN}[1/5] Scrubbing systemic package configurations (APT)...{RESET}")
    _print_step_result("apt-get clean",       _run(['apt-get', 'clean'], use_sudo=True))
    _print_step_result("apt-get autoremove",  _run(['apt-get', 'autoremove', '-y'], use_sudo=True))

    print(f"\n  {CYAN}[2/5] Compressing operational infrastructure logging (Journal Vacuum)...{RESET}")
    _print_step_result("journalctl --vacuum-time=1d",
                       _run(['journalctl', '--vacuum-time=1d'], use_sudo=True))

    print(f"\n  {CYAN}[3/5] Cleaning background rendering framework layouts (Thumbnails)...{RESET}")
    for tp in thumb_paths:
        ok = delete_path_content(tp, delete_root=True)
        _print_step_result(str(tp), ok)

    print(f"\n  {CYAN}[4/5] Signaling Linux Kernel memory virtual pages (Drop Caches)...{RESET}")
    try:
        subprocess.run(['sudo', 'sync'], check=True, capture_output=True, timeout=15)
        r = subprocess.run(
            "echo 3 | sudo tee /proc/sys/vm/drop_caches",
            shell=True, capture_output=True, timeout=10
        )
        _print_step_result("drop_caches signal", r.returncode == 0)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        _print_step_result("drop_caches signal", False)
        print(f"    {DIM}{e}{RESET}")

    print(f"\n  {CYAN}[5/5] Resetting dynamic allocation paths (/tmp maps)...{RESET}")
    _print_step_result("/tmp core content wipe", delete_path_content(Path("/tmp"), delete_root=False))

    print(f"\n  {GREEN}[✓] Success: Core Sovereign automation stack optimization pipeline concluded.{RESET}")
    wait_for_enter()


def _sync_sudo_status() -> None:
    global HAS_SUDO_PERM
    if HAS_SUDO_PERM:
        if not check_sudo_status() and os.getuid() != 0:
            HAS_SUDO_PERM = False
    else:
        if check_sudo_status():
            HAS_SUDO_PERM = True


def main_menu() -> None:
    global HAS_SUDO_PERM

    if check_sudo_status() or os.getuid() == 0:
        HAS_SUDO_PERM = True
        clear_screen()
        app_logo()
        print(f"  {GREEN}[✓] Existing session identified. Sudo privilege level active.{RESET}")
        time.sleep(1.2)
    else:
        attempt_elevation(show_intro=True)

    while True:
        _sync_sudo_status()
        clear_screen()
        app_logo()

        sudo_tag = (f"{GREEN}Privileged{RESET}" if HAS_SUDO_PERM
                    else f"{YELLOW}User-Only{RESET}")
        lock     = lambda: (f"  {GREEN}[Unlocked]{RESET}" if HAS_SUDO_PERM
                            else f"  {RED}[Sudo Required]{RESET}")

        print(f"  {CYAN}[+] Available Optimization Frameworks  [{sudo_tag}]:{RESET}\n")
        print(f"    {GREEN}[1]{RESET}  Scan & Purge: User Profile Cache")
        print(f"    {GREEN}[2]{RESET}  Scan & Purge: System Engine Core{lock()}")
        print(f"    {GREEN}[3]{RESET}  Purge Superseded Snap Packages{lock()}")
        print(f"    {GREEN}[4]{RESET}  Execute Sovereign Macro (Clean All){lock()}")
        if not HAS_SUDO_PERM:
            print(f"\n    {DIM}[5]  Elevate runtime execution layer to Sudo{RESET}")
        print(f"\n    {RED}[0]{RESET}  Terminate Optimization Session")

        valid = ["0", "1", "2", "3", "4"] + (["5"] if not HAS_SUDO_PERM else [])
        choice = ask_choice(valid)

        if choice == "1":
            manage_user_cache()

        elif choice in ("2", "3", "4"):
            if not HAS_SUDO_PERM:
                print(f"\n  {YELLOW}[!] Action Blocked: Elevated clearance credentials required.{RESET}")
                if ask_yes_no(f"  [?] Authenticate administrator context right now?"):
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
            print(f"\n  {GREEN}[✓] Session context dropped cleanly. Goodbye!{RESET}\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}[!] Execution interrupted by hardware termination signal (Ctrl+C).{RESET}\n")
        sys.exit(0)
