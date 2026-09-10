"""Module [3]: Snap Version Scrubber."""
import re
import subprocess

from core import state
from core.fs_utils import _run
from ui.colors import CYAN, YELLOW, RED, GREEN, DIM, RESET
from ui.terminal import clear_screen, header, center_print, ask_yes_no, wait_for_enter


def clean_snap_old_versions() -> None:
    clear_screen(); header("Snap Version Scrubber")
    if not state.HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges required.{RESET}"); wait_for_enter(); return
    center_print(f"{CYAN}  [*] Searching for disabled Snap revisions...{RESET}\n")
    try: out = subprocess.check_output(["snap", "list", "--all"], text=True)
    except Exception: out = ""
    disabled = []
    for line in out.splitlines()[1:]:
        if re.search(r'\bdisabled\b', line, re.IGNORECASE):
            parts = re.split(r'\s{2,}', line.strip())
            if not parts: parts = line.split()
            if len(parts) >= 3:
                name = parts[0]; rev = parts[2]
                if not rev.isdigit() and len(parts) > 3: rev = parts[3]
                disabled.append((name, rev))
    if not disabled:
        center_print(f"{GREEN}  [✓] No old Snap revisions found.{RESET}"); wait_for_enter(); return
    for name, rev in disabled: center_print(f"  {DIM}→{RESET}  {name:<28}  {DIM}[rev: {rev}]{RESET}")
    print()

    prompt = "Permanently remove these disabled revisions?" if not state.IS_DRY_RUN else "Simulate Snap revision removal?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Removing' if not state.IS_DRY_RUN else 'Simulating removal of'} revisions...{RESET}\n")
        for n, r in disabled:
            ok = _run(['snap', 'remove', n, f'--revision={r}'], True)
            status = f"{GREEN}✓" if ok else f"{RED}✗"
            center_print(f"    [{status}{RESET}]  {n} (rev {r})")
        msg = "Old revisions removed." if not state.IS_DRY_RUN else "Dry run complete. No Snaps were modified."
        print(); center_print(f"{GREEN}  [✓] Done: {msg}{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No revisions were removed.{RESET}")
    wait_for_enter()
