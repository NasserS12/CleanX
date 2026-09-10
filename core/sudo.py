"""Sudo / privilege helpers."""
import os
import subprocess
import time
from pathlib import Path

from core import state
from ui.colors import GREEN, YELLOW, RED, CYAN, BOLD, RESET
from ui.terminal import clear_screen, center_print, ask_yes_no, header  # noqa: F401


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
    # Local import to avoid a circular import with main.app_logo at module
    # load time (app_logo lives in main.py, which imports this module).
    from main import app_logo

    if show_intro:
        clear_screen(); app_logo()
        center_print(f"{CYAN}{BOLD}[+] Privilege Initialization{RESET}")
        print()
        center_print("  Sudo rights are required for deep system cleaning.")
        center_print("  Restricted mode is available without elevation.")
        print()
        from ui.terminal import _divider
        _divider()
    if show_intro and not ask_yes_no(f"{YELLOW}[?] Elevate session to Sudo now?{RESET}"):
        state.HAS_SUDO_PERM = False
        print(); center_print(f"{YELLOW}  [-] Restricted mode authorized. System pathways locked.{RESET}")
        time.sleep(2.0); return False
    print(); center_print(f"{CYAN}  [*] Interrogating privilege stack...{RESET}")
    try:
        result = subprocess.run(['sudo', '-v'], check=False)
        if result.returncode == 0:
            state.HAS_SUDO_PERM = True
            center_print(f"{GREEN}  [✓] Authentication successful. High-privilege mode active.{RESET}")
            time.sleep(1.5); return True
        else:
            state.HAS_SUDO_PERM = False
            center_print(f"{RED}  [✗] Authentication failed. Dropping back to User mode.{RESET}")
            time.sleep(2.0); return False
    except Exception:
        state.HAS_SUDO_PERM = False
        return False
