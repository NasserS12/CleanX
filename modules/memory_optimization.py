"""Module [8]: Engine Optimization — RAM Cache & Swap Reset."""
import subprocess

from core import state
from core.fs_utils import _run
from ui.colors import BOLD, CYAN, DIM, GREEN, RED, RESET, WHITE, YELLOW
from ui.terminal import (
    _divider,
    ask_yes_no,
    center_print,
    clear_screen,
    header,
    wait_for_enter,
)


def manage_memory_optimization() -> None:
    clear_screen(); header("Engine Optimization: RAM & Swap Reset")
    if not state.HAS_SUDO_PERM:
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
