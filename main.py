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


__version__ = "1.1.0"


def app_logo() -> None:
    print()
    plain_brand = "◆ CleanX   Cache Analytics & Deep Scrub for Ubuntu Systems"
    center_print(f"{CYAN}{BOLD}◆ CleanX{RESET}   {DIM}Cache Analytics & Deep Scrub for Ubuntu Systems{RESET}")
    center_print(f"{YELLOW}{'─' * len(plain_brand)}{RESET}")
    center_print(f"{DIM}v{__version__} · Dev by Nasser{RESET}")
    print()


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
        mode      = f"{GREEN}{BOLD}Privileged{RESET}" if state.HAS_SUDO_PERM else f"{YELLOW}{BOLD}Restricted{RESET}"
        lock_word = f"{GREEN}Unlocked{RESET}" if state.HAS_SUDO_PERM else f"{RED}Locked{RESET}"
        dry_word  = f"{YELLOW}{BOLD}Dry Run{RESET}" if state.IS_DRY_RUN else f"{DIM}Real Mode{RESET}"
        sudo_tag  = "" if state.HAS_SUDO_PERM else f"  {DIM}(sudo){RESET}"

        center_print(
            f"{DIM}[{RESET}{mode}{DIM}]{RESET}  {DIM}[{RESET}{lock_word}{DIM}]{RESET}  {DIM}[{RESET}{dry_word}{DIM}]{RESET}"
        )
        print(); _divider(); print()

        menu_width = min(cols() - 4, 68)
        indent = max(0, (cols() - menu_width) // 2)
        def m(text: str, pad: int = 0) -> None:
            line = " " * pad + text
            plain = re.sub(r'\033\[[0-9;]*m', '', line)
            if len(plain) > menu_width:
                print(" " * indent + line)
            else:
                print(" " * indent + line + " " * max(0, menu_width - len(plain)))

        m(f"{CYAN}{BOLD}CACHE & STORAGE{RESET}")
        m(f"{GREEN}{BOLD}[1]{RESET} Deep Scan & Purge · User Profile Cache", pad=1)
        m(f"{GREEN}{BOLD}[2]{RESET} Integrated Purge · System Engine Cache{sudo_tag}", pad=1)
        print()
        m(f"{CYAN}{BOLD}PACKAGES & PROGRAMS{RESET}")
        m(f"{GREEN}{BOLD}[3]{RESET} Snap Version Scrub · Old Revisions{sudo_tag}", pad=1)
        m(f"{GREEN}{BOLD}[4]{RESET} Orphaned Package Discovery{sudo_tag}", pad=1)
        m(f"{GREEN}{BOLD}[7]{RESET} Program Deep Removal · Residual Files{sudo_tag}", pad=1)
        print()
        m(f"{CYAN}{BOLD}SYSTEM{RESET}")
        m(f"{GREEN}{BOLD}[5]{RESET} Large & Aged File Radar", pad=1)
        m(f"{GREEN}{BOLD}[6]{RESET} Journal Log Vacuum{sudo_tag}", pad=1)
        m(f"{GREEN}{BOLD}[8]{RESET} RAM Cache & Swap Reset{sudo_tag}", pad=1)
        print()
        m(f"{CYAN}{BOLD}SESSION{RESET}")
        dry_color = YELLOW if state.IS_DRY_RUN else DIM
        dry_label = "Disable" if state.IS_DRY_RUN else "Enable"
        m(f"{dry_color}{BOLD}[9]{RESET} {dry_label} Dry Run Mode", pad=1)
        m(f"{WHITE}{BOLD}[H]{RESET} Help / About Dry Run Mode", pad=1)
        if not state.HAS_SUDO_PERM:
            m(f"{DIM}[10] Elevate Session to Sudo{RESET}", pad=1)
        m(f"{RED}{BOLD}[0]{RESET} Exit CleanX", pad=1)

        print(); _divider(); print()
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
