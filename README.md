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
- A full report is shown of everything that *would* happen

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

## Built-in Safety

CleanX includes a protection layer to prevent destructive mistakes:

- **Critical system paths are blocked** — `/etc`, `/usr`, `/bin`, `/boot`, and others cannot be deleted
- **Home directory is protected** from full removal
- **Virtual filesystems are off-limits** — `/proc`, `/sys`, `/dev` cannot be scanned or touched
- **Symlink traversal is prevented** via `path.resolve()` to guard against path manipulation

---


## Notes

- CleanX is designed for **Ubuntu** and Debian-based distributions.
- Some features (Snap, APT) may not be available on other distros.
- **Always run Dry Run first** if you are using CleanX for the first time.

---

## License

This project is licensed under the [MIT License](LICENSE).
