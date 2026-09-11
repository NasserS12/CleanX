<div align="center">

```
 ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██╗  ██╗
██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║╚██╗██╔╝
██║     ██║     █████╗  ███████║██╔██╗ ██║ ╚███╔╝ 
██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║ ██╔██╗ 
╚██████╗███████╗███████╗██║  ██║██║ ╚████║██╔╝ ██╗
 ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
```

**High-Performance Cache Analytics & Deep Scrub for Ubuntu Systems**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%20%2F%20Linux-orange?style=flat-square&logo=linux)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

---

## What is CleanX?

**CleanX** is an interactive command-line tool written in Python, built to safely scan and reclaim disk space on Ubuntu/Linux systems. It combines a polished terminal UI with built-in safeguards that prevent accidental deletion of critical system files.

---

## Features

| # | Module | Description |
|:---:|---|---|
| `1` | **User Cache Sweeper** | Clears app caches, browser data, VS Code, npm, and compiled Python bytecode (`__pycache__`) |
| `2` | **System Cache Sweeper** | Purges APT archives, core dumps, archived logs, and `/tmp` contents |
| `3` | **Snap Version Scrubber** | Removes old disabled Snap package revisions |
| `4` | **Orphaned Package Discovery** | Detects and removes unused dependencies via `apt-get autoremove` |
| `5` | **Large & Aged File Radar** | Advanced search for the largest and oldest files with custom size and age filters |
| `6` | **Journal Log Vacuum** | Cleans systemd journal logs by time limit or size budget |
| `7` | **Program Deep Removal** | Searches all package managers (APT/Snap/Flatpak), checks reverse deps, and purges residual config/data files |
| `8` | **RAM & Swap Reset** | Flushes page cache, dentries, and inodes; cycles swap to reclaim memory |

---

## Dry Run Mode

CleanX includes a **Dry Run** mode that simulates every operation without touching a single file — perfect for auditing before committing to a cleanup.

- No files are deleted
- No system commands are executed
- A full report is shown of everything that *would* happen — including anything that would have been **blocked** by the safety checks below, so a Dry Run gives you an accurate preview of the real run

Toggle it on or off from the main menu by pressing `9`.

---

## Requirements

- Python **3.10** or higher
- **Ubuntu / Debian-based** Linux
- **sudo** privileges for system-level operations (APT, Snap, journal logs)

---

## Usage

```bash
# Clone the repository
git clone https://github.com/NasserS12/cleanx.git
cd cleanx

# Run the script
python3 main.py

# Or with sudo directly
sudo python3 main.py
```

> If not launched with `sudo`, CleanX will prompt for elevation when needed.

---

## Project Structure

The codebase is organized by responsibility. `main.py` is the entry point only — it wires together the menu loop and delegates all real work to the modules below.

```
cleanx/
├── main.py                     # Entry point — main menu & startup banner
├── requirements.txt
├── ui/
│   ├── colors.py                 # ANSI colors
│   └── terminal.py               # Echo control, centered printing, prompts
├── core/
│   ├── state.py                  # Shared app state (sudo status, Dry Run flag)
│   ├── sudo.py                   # Privilege checks & real-user home resolution
│   └── fs_utils.py                # Size scanning, safe deletion, protected-path guard
└── modules/
    ├── user_cache.py              # [1] User Cache Sweeper
    ├── system_cache.py            # [2] System Cache Sweeper
    ├── snap_cleanup.py            # [3] Snap Version Scrubber
    ├── orphaned_packages.py       # [4] Orphaned Package Discovery
    ├── large_files.py             # [5] Large & Aged File Radar
    ├── journal_logs.py            # [6] Journal Log Vacuum
    ├── program_removal.py         # [7] Program Deep Removal
    ├── memory_optimization.py     # [8] RAM & Swap Reset
    └── help.py                    # Dry Run help screen
```

---

## Built-in Safety

CleanX includes a protection layer, implemented in `core/fs_utils.py`, to prevent destructive mistakes. Every deletion in the app — regardless of which feature triggered it — goes through this single function, so the guarantees below apply uniformly:

- **Critical system paths are blocked.** `delete_path_content()` refuses to delete anything that resolves under `/etc`, `/usr`, `/bin`, `/sbin`, `/lib`, `/lib32`, `/lib64`, `/boot`, `/proc`, `/sys`, or `/dev` — no matter which feature or user-supplied path produced the request. A blocked attempt prints `[BLOCKED]` and is reported the same way in both Dry Run and real mode.
- **Home directory is protected from full removal.** The resolved target is compared against the current user's home directory (correctly resolved even when running via `sudo`); an exact match is refused. Subdirectories and their contents (e.g. `~/.cache/...`) remain cleanable as normal — only removing the home directory *itself* is blocked.
- **Symlink traversal is prevented via `path.resolve()`.** Before checking a real file or directory against the protected list above, its path is fully resolved (following any symlinks). A symlink planted inside an otherwise-allowed cache folder that points into a protected location cannot be used to smuggle a deletion into that location.
- **Removing a symlink itself is always allowed**, regardless of what it points to — unlinking a symlink never touches its target, which is what makes the "Broken System Symlinks" cleanup (part of the User Cache Sweeper) work correctly even for dangling links that "point at" a protected path.

**One deliberate exception, documented here for clarity:** the RAM & Swap Reset feature (`[8]`) intentionally writes to `/proc/sys/vm/drop_caches` as part of a standard, well-known Linux technique for releasing page cache. This is a narrow, hardcoded write — not a deletion and not a user-directed scan of `/proc` — so it is unaffected by (and does not need to be covered by) the deletion guard above.

---

## Development Notes

This project was built with AI-assisted development (Claude) under my
direction — I defined the architecture, reviewed every change, wrote
the test cases, and made all design decisions. AI was used as a
pair-programming tool, not an autonomous author.


## Usage Notes

- CleanX is designed for **Ubuntu** and Debian-based distributions.
- Some features (Snap, APT) may not be available on other distros.
- **Always run Dry Run first** if you are using CleanX for the first time.

---

## License

This project is licensed under the [MIT License](LICENSE).
