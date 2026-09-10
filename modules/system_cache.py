"""Module [2]: System Cache Sweeper."""
from pathlib import Path

from core import state
from core.fs_utils import (
    scan_described_paths, print_described_table, delete_path_content,
    format_size, _find_dead_logs, _run,
)
from ui.colors import CYAN, YELLOW, RED, GREEN, RESET
from ui.terminal import clear_screen, header, center_print, ask_yes_no, wait_for_enter


def manage_system_cache() -> None:
    clear_screen(); header("System Cache Sweeper")
    if not state.HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: This option requires Sudo privileges.{RESET}"); wait_for_enter(); return
    targets = [
        {"label": "APT Package Archives", "path": "/var/cache/apt/archives", "desc": "Local repository of downloaded .deb installer files.", "is_important": True},
        {"label": "Systemd Crash Core Dumps", "path": "/var/lib/systemd/coredump", "desc": "Massive frozen snapshots of crashed applications.", "is_important": True},
        {"label": "Manual Page Cache", "path": "/var/cache/man", "desc": "Pre-rendered manual pages for system documentation.", "is_important": False},
        {"label": "Apache2 Server Cache", "path": "/var/cache/apache2", "desc": "Temporary web server assets and module caches.", "is_important": False},
        {"label": "App Store Info Cache", "path": "/var/cache/app-info", "desc": "Ubuntu Software metadata and catalog icons.", "is_important": False},
        {"label": "Software Catalog Cache", "path": "/var/cache/swcatalog", "desc": "AppStream software metadata for Linux repositories.", "is_important": False},
        {"label": "Temporary Files (/tmp)", "path": "/tmp", "desc": "System-wide temporary directory for all root processes.", "is_important": True},
    ]
    center_print(f"{CYAN}  [*] Scanning architectural system cache paths...{RESET}\n")
    results = scan_described_paths(targets)
    dead_logs, logs_size = _find_dead_logs(Path("/var/log"))
    results.append({"label": "Archived System Logs", "path": dead_logs, "desc": "Old versions of system logs (.gz and .old) no longer in use.", "is_important": False, "exists": bool(dead_logs), "size_bytes": logs_size, "size_fmt": format_size(logs_size), "is_list": True})
    total = print_described_table(results)
    if total == 0:
        center_print(f"{GREEN}  [✓] Clean: System engine caches are empty.{RESET}"); wait_for_enter(); return

    if state.IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No system files will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. System files will be lost.{RESET}")

    prompt = "Purge all listed systemic core engines and cache layouts?" if not state.IS_DRY_RUN else "Simulate systemic purge?"
    if not ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{YELLOW}  [-] Aborted: Core systemic architecture preserved safely.{RESET}"); wait_for_enter(); return
    print(); center_print(f"{CYAN}  [1/2] Pruning systemic package databases...{RESET}")
    _run(['apt-get', 'clean'], True); _run(['apt-get', 'autoremove', '-y'], True)
    center_print(f"    [{GREEN}✓{RESET}]  APT cleanup complete")
    center_print(f"{CYAN}  [2/2] Executing deep deployment scrub routines...{RESET}")
    for r in results:
        if r["exists"] and "APT" not in r["label"]:
            paths = r["path"] if r.get("is_list") else [r["path"]]
            for t in paths: delete_path_content(Path(t), delete_root=False)
            center_print(f"    [{GREEN}✓{RESET}]  {r['label']}")

    msg = "System structural caches purged successfully." if not state.IS_DRY_RUN else "Dry run complete. No system files were removed."
    print(); center_print(f"{GREEN}  [✓] Success: {msg}{RESET}")
    wait_for_enter()
