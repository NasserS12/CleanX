"""Module [4]: Orphaned Package Discovery."""
import subprocess

from core import state
from core.fs_utils import _run
from ui.colors import CYAN, YELLOW, RED, GREEN, DIM, RESET
from ui.terminal import clear_screen, header, center_print, ask_yes_no, wait_for_enter


def manage_orphaned_packages() -> None:
    clear_screen(); header("Orphaned Package Discovery")
    if not state.HAS_SUDO_PERM:
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

    prompt = "Purge all listed orphaned dependencies?" if not state.IS_DRY_RUN else "Simulate orphaned package purge?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] Executing systemic purge...{RESET}")
        if _run(['apt-get', 'autoremove', '-y'], True):
            msg = "System free of orphaned artifacts." if not state.IS_DRY_RUN else "Dry run complete. No packages were removed."
            center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
        else: center_print(f"{RED}  [✗] Failure: Purge routine encountered an error.{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No packages were removed.{RESET}")
    wait_for_enter()
