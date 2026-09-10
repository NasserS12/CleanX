#!/usr/bin/env python3
"""CleanX — High-Performance Cache Analytics & Deep Scrub for Ubuntu Systems.

Entry point only. All feature logic lives in modules/; shared UI and
core helpers live in ui/ and core/. See README.md for the module map.
"""
import os
import re
import sys
import time

from core import state
from core.sudo import check_sudo_status, attempt_elevation
from ui.colors import GREEN, YELLOW, RED, CYAN, WHITE, BOLD, DIM, RESET
from ui.terminal import clear_screen, cols, center_print, _divider, ask_choice

from modules.user_cache import manage_user_cache
from modules.system_cache import manage_system_cache
from modules.snap_cleanup import clean_snap_old_versions
from modules.orphaned_packages import manage_orphaned_packages
from modules.large_files import manage_large_files
from modules.journal_logs import manage_journal_logs
from modules.program_removal import remove_program_and_residuals
from modules.memory_optimization import manage_memory_optimization
from modules.help import show_dry_run_help


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


def main_menu() -> None:
    if check_sudo_status() or os.getuid() == 0:
        state.HAS_SUDO_PERM = True
        clear_screen(); app_logo()
        center_print(f"{GREEN}  [✓] Sudo authorization active.{RESET}")
        time.sleep(1.0)
    else:
        attempt_elevation(show_intro=True)

    while True:
        if not state.HAS_SUDO_PERM:
            if check_sudo_status(): state.HAS_SUDO_PERM = True
        else:
            if not check_sudo_status() and os.getuid() != 0: state.HAS_SUDO_PERM = False
        clear_screen(); app_logo()
        mode = f"{GREEN}{BOLD}Privileged{RESET}" if state.HAS_SUDO_PERM else f"{YELLOW}{BOLD}Restricted{RESET}"
        lock = f"{GREEN}[Unlocked]{RESET}" if state.HAS_SUDO_PERM else f"{RED}[Locked]{RESET}"
        dry  = f"{YELLOW}{BOLD}[DRY RUN ACTIVE]{RESET}" if state.IS_DRY_RUN else f"{DIM}[Real Mode]{RESET}"

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

        dry_color = YELLOW if state.IS_DRY_RUN else DIM
        dry_label = "Disable" if state.IS_DRY_RUN else "Enable"
        print()
        m(f"  {dry_color}{BOLD}[9]{RESET}  {dry_label} Dry Run Mode (No deletion)")
        m(f"  {WHITE}{BOLD}[H]{RESET}  Help / About Dry Run Mode")

        if not state.HAS_SUDO_PERM:
            m(f"  {DIM}[10]  Elevate Session to Sudo{RESET}")
        print(); _divider(); print()
        m(f"  {RED}{BOLD}[0]{RESET}  {DIM}Exit CleanX{RESET}")
        print()
        valid = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "H", "h"] + (["10"] if not state.HAS_SUDO_PERM else [])
        choice = ask_choice(valid)
        if choice == "1": manage_user_cache()
        elif choice in ("2", "3", "4", "6", "7", "8"):
            if not state.HAS_SUDO_PERM:
                print(); center_print(f"{YELLOW}  [!] Action blocked: Sudo privileges required.{RESET}")
                from ui.terminal import ask_yes_no
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
            state.IS_DRY_RUN = not state.IS_DRY_RUN
            center_print(f"{YELLOW}  [*] Dry Run Mode {'Enabled' if state.IS_DRY_RUN else 'Disabled'}.{RESET}")
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
