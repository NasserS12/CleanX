"""Module [1]: User Cache Sweeper."""
from pathlib import Path

from core import state
from core.fs_utils import (
    _find_recursive_targets,
    delete_path_content,
    format_size,
    print_described_table,
    scan_described_paths,
)
from core.sudo import get_user_home
from ui.colors import CYAN, GREEN, RED, RESET, YELLOW
from ui.terminal import ask_yes_no, center_print, clear_screen, header, wait_for_enter


def manage_user_cache() -> None:
    clear_screen(); header("User Cache Sweeper")
    home = get_user_home()
    targets = [
        {"label": "Node Package Manager (npm)", "path": str(home / ".npm"), "desc": "Download cache for Javascript development libraries.", "is_important": False},
        {"label": "User Temporary Staging", "path": str(home / "tmp"), "desc": "Personal temporary folder for miscellaneous user data.", "is_important": False},
        {"label": "Snap Execution Cache", "path": str(home / "snap/common/.cache"), "desc": "Cached assets specifically for Snap package operations.", "is_important": True},
        {"label": "Command History Log", "path": str(home / ".bash_history"), "desc": "Stored history of your terminal execution commands.", "is_important": False},
        {"label": "System Trash Bin", "path": str(home / ".local/share/Trash"), "desc": "Contents currently residing in your Recycle Bin.", "is_important": False},
        {"label": "VS Code Interface Cache", "path": str(home / ".config/Code/Cache"), "desc": "Temporary Electron UI files for Visual Studio Code.", "is_important": False},
        {"label": "VS Code Script Cache", "path": str(home / ".config/Code/CachedData"), "desc": "Compiled script versions for faster VS Code launch.", "is_important": False},
        {"label": "VS Code Extension Cache", "path": str(home / ".vscode/extensions/.cache"), "desc": "Metadata and cached assets for your IDE plugins.", "is_important": False},
        {"label": "Firefox Web Cache", "path": str(home / ".cache/mozilla/firefox"), "desc": "Stored website snapshots and assets from Firefox.", "is_important": False},
        {"label": "Chrome Web Cache", "path": str(home / ".cache/google-chrome"), "desc": "Stored website snapshots and assets from Chrome.", "is_important": False},
        {"label": "Brave Web Cache", "path": str(home / ".cache/BraveSoftware/Brave-Browser"), "desc": "Stored website snapshots and assets from Brave.", "is_important": False},
    ]
    center_print(f"{CYAN}  [*] Initiating comprehensive user profile scan...{RESET}\n")
    results = scan_described_paths(targets)
    pyc_paths, pyc_size = _find_recursive_targets(home, "__pycache__")
    results.append({"label": "Python Bytecode Junk", "path": pyc_paths, "desc": "Recursive __pycache__ clusters found in your project folders.", "is_important": False, "exists": bool(pyc_paths), "size_bytes": pyc_size, "size_fmt": format_size(pyc_size), "is_list": True})
    dead_links, _ = _find_recursive_targets(home, "broken_symlinks")
    results.append({"label": "Broken System Symlinks", "path": dead_links, "desc": "Dead shortcuts pointing to non-existent file locations.", "is_important": True, "exists": bool(dead_links), "size_bytes": 0, "size_fmt": f"{len(dead_links)} links", "is_list": True})
    total = print_described_table(results, title=f"Target Profile: {CYAN}{home}{RESET}")
    if total == 0 and not any(r["label"] == "Broken System Symlinks" and r["exists"] for r in results):
        center_print(f"{GREEN}  [✓] Clean: No cache clutter detected.{RESET}"); wait_for_enter(); return

    if state.IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No files will be deleted — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT. Files will NOT go to Trash.{RESET}")

    prompt = "Wipe all listed profile caches?" if not state.IS_DRY_RUN else "Simulate profile cache wipe?"
    if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
        print(); center_print(f"{CYAN}  [*] {'Erasing' if not state.IS_DRY_RUN else 'Simulating erasure of'} files...{RESET}")
        for r in results:
            if r["exists"]:
                paths = r["path"] if r.get("is_list") else [r["path"]]
                for t in paths: delete_path_content(Path(t), delete_root=r.get("is_list", False))
                center_print(f"    [{GREEN}✓{RESET}]  {r['label']}")
        msg = "User profile scrubbed successfully." if not state.IS_DRY_RUN else "Dry run complete. No files were removed."
        print(); center_print(f"{GREEN}  [✓] Done: {msg}{RESET}")
    else: print(); center_print(f"{YELLOW}  [-] Aborted: No data was removed.{RESET}")
    wait_for_enter()
