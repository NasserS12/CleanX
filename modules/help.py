"""Help screen: About Dry Run Mode."""
from ui.colors import BOLD, CYAN, DIM, GREEN, RESET, WHITE, YELLOW
from ui.terminal import _divider, center_print, clear_screen, header, wait_for_enter


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
    center_print(f"{DIM}Press [9] on the main menu to toggle this mode on/off.{RESET}")
    wait_for_enter()
