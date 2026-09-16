"""Terminal I/O helpers: echo control, centered printing, headers,
and yes/no / multiple-choice prompts.
"""
import os
import re
import shutil
import sys
import time
from contextlib import contextmanager

from ui.colors import BOLD, CYAN, DIM, RED, RESET, WHITE


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
