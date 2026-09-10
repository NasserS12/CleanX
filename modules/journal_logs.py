"""Module [6]: Journalctl Log Vacuum."""
import subprocess

from core import state
from core.fs_utils import _run
from ui.colors import CYAN, YELLOW, RED, GREEN, WHITE, BOLD, DIM, RESET
from ui.terminal import clear_screen, header, center_print, cols, _divider, ask_choice, ask_yes_no, wait_for_enter


def manage_journal_logs() -> None:
    clear_screen(); header("Journalctl Log Vacuum")
    if not state.HAS_SUDO_PERM:
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

    if state.IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No log entries will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. Log entries will be lost.{RESET}")

    prompt = f"Execute vacuum with limit '{limit}'?" if not state.IS_DRY_RUN else "Simulate journal vacuum?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Vacuuming' if not state.IS_DRY_RUN else 'Simulating vacuum of'} journal logs...{RESET}")
        if _run(cmd, True):
            msg = "Journal logs vacuumed successfully." if not state.IS_DRY_RUN else "Dry run complete. No logs were removed."
            center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
        else:
            center_print(f"{RED}  [✗] Failure: Vacuum routine encountered an error.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: Logs preserved.{RESET}")
    wait_for_enter()
