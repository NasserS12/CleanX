"""Module [7]: Program Deep Removal & Residual Purge.

Detects the package manager (APT/Snap/Flatpak), checks reverse
dependencies against a critical-package blacklist, finds residual
config/cache/data files, and removes both — safely.
"""
import re
import subprocess
import time
from pathlib import Path

from core import state
from core.fs_utils import _apt_env, _run, _walk_size, delete_path_content, format_size
from core.sudo import get_user_home
from ui.colors import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from ui.terminal import (
    _divider,
    ask_choice,
    ask_yes_no,
    center_print,
    clear_screen,
    cols,
    header,
    wait_for_enter,
)

_CRITICAL_PACKAGES: set[str] = {
    "linux-base", "linux-image", "linux-headers", "grub", "grub2",
    "grub-common", "grub-pc", "grub-efi", "systemd", "systemd-sysv",
    "init", "udev", "dbus", "libc6", "libc-bin", "apt", "dpkg",
    "bash", "coreutils", "util-linux", "mount", "sudo", "passwd",
    "login", "adduser", "base-files", "base-passwd", "sysvinit-utils",
    "python3", "python3-minimal", "libpython3", "network-manager",
    "ifupdown", "iproute2", "openssh-server", "openssh-client",
    "gnome-shell", "ubuntu-desktop", "xorg", "xserver-xorg",
}

_PKG_ALIASES: dict[str, list[str]] = {
    "brave":            ["BraveSoftware", "brave", "brave-browser"],
    "brave-browser":    ["BraveSoftware", "brave", "brave-browser"],
    "google-chrome":    ["google-chrome", "google", "Google"],
    "chromium":         ["chromium", "chromium-browser"],
    "chromium-browser": ["chromium", "chromium-browser"],
    "firefox":          ["firefox", "mozilla", "Mozilla"],
    "thunderbird":      ["thunderbird", "Thunderbird", "mozilla"],
    "vlc":              ["vlc"],
    "gimp":             ["GIMP", "gimp"],
    "libreoffice":      ["libreoffice", "LibreOffice"],
    "vscode":           ["Code", "code", "vscode"],
    "code":             ["Code", "code", "vscode"],
    "discord":          ["discord", "Discord"],
    "slack":            ["Slack", "slack"],
    "spotify":          ["spotify", "Spotify"],
    "telegram-desktop": ["TelegramDesktop", "telegram-desktop"],
    "zoom":             ["zoom", "Zoom"],
    "obs-studio":       ["obs-studio", "obs"],
    "steam":            ["steam", "Steam"],
    "skype":            ["skypeforlinux", "Skype"],
}


def _detect_package_manager(pkg: str) -> str | None:
    """
    Returns the package manager that owns the package:
    'apt', 'snap', 'flatpak', or None if not found.

    For flatpak: pkg may be a full app-ID (e.g. com.mitchellh.micro)
    or a short name (e.g. micro). We match against the last dotted
    component so both forms are recognised correctly.
    """
    try:
        r = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and "install ok installed" in r.stdout:
            return "apt"
    except Exception:
        pass

    try:
        r = subprocess.run(["snap", "list", pkg], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and pkg in r.stdout:
            return "snap"
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            pkg_lower = pkg.lower()
            for line in r.stdout.splitlines():
                app_id = line.strip()
                if not app_id:
                    continue
                short = app_id.split(".")[-1].lower()
                if app_id.lower() == pkg_lower or short == pkg_lower:
                    return "flatpak"
    except Exception:
        pass
    return None


def _get_apt_reverse_deps(pkg: str) -> list[str]:
    """
    Returns a list of installed packages that depend on `pkg`.
    Uses apt-cache rdepends + dpkg-query to filter only installed ones.
    """
    try:
        r = subprocess.run(
            ["apt-cache", "rdepends", "--installed", pkg],
            capture_output=True, text=True, timeout=15 , env=_apt_env()

        )
        deps: list[str] = []
        capture = False
        for line in r.stdout.splitlines():
            if line.strip() == "Reverse Depends:":
                capture = True
                continue
            if capture:
                dep = line.strip().lstrip("|").strip()
                if dep:
                    deps.append(dep)
        return list(set(deps))
    except Exception:
        return []


def _collect_residuals(pkg: str, pm: str | None = None) -> list[dict]:
    """
    Builds a list of residual paths associated with `pkg`.
    Checks standard XDG dirs, Snap user data, known aliases, and
    performs a glob search in ~/.config / ~/.local/share for partial matches.

    For Flatpak: pkg is the full App ID (e.g. com.mitchellh.micro).
    The primary sandbox data lives at ~/.var/app/<AppID>/ and contains
    all user config/cache/data. We also derive the short name from the
    last dotted segment to search common XDG dirs.
    """
    home = get_user_home()

    if pm == "flatpak" and "." in pkg:
        short_name = pkg.split(".")[-1]
        search_names: list[str] = list(dict.fromkeys(
            [pkg, short_name]
            + _PKG_ALIASES.get(short_name, [])
            + _PKG_ALIASES.get(pkg, [])
        ))
    else:
        short_name = pkg
        search_names = list(dict.fromkeys([pkg] + _PKG_ALIASES.get(pkg, [])))

    raw_candidates: list[tuple[Path, str]] = []

    if pm == "flatpak":
        flatpak_var = home / ".var" / "app" / pkg
        raw_candidates.append((flatpak_var, f"Flatpak user data (~/.var/app/{pkg})"))

    for name in search_names:
        raw_candidates += [
            (home / ".config"      / name,  f"User config (~/.config/{name})"),
            (home / ".local/share" / name,  f"User data (~/.local/share/{name})"),
            (home / ".cache"       / name,  f"User cache (~/.cache/{name})"),
            (home / f".{name}",             f"Hidden home dir (~/.{name})"),
            (home / f".{name}rc",           f"RC dotfile (~/.{name}rc)"),
        ]

    raw_candidates.append((home / "snap" / pkg, f"Snap user data (~/snap/{pkg})"))

    glob_term = short_name.lower()
    for search_base, label_prefix, short_base in [
        (home / ".config",      "User config (glob)", "~/.config"),
        (home / ".local/share", "User data (glob)",   "~/.local/share"),
        (home / ".cache",       "User cache (glob)",  "~/.cache"),
    ]:
        try:
            if search_base.is_dir():
                for child in search_base.iterdir():
                    if re.search(r'\b' + re.escape(glob_term) + r'\b', child.name.lower()):
                        already = any(p == child for p, _ in raw_candidates)
                        if not already:
                            raw_candidates.append((child, f"{label_prefix} ({short_base}/{child.name})"))
        except PermissionError:
            pass

    seen: set[Path] = set()
    residuals: list[dict] = []
    for path, label in raw_candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.exists():
            continue
        size = _walk_size(path)
        residuals.append({
            "path":       path,
            "label":      label,
            "size_bytes": size,
            "size_fmt":   format_size(size),
            "exists":     True,
        })
    return residuals


def _search_packages(query: str) -> list[tuple[str, str]]:
    """Search all package managers for installed packages with names containing *query*.
    Returns a sorted list of (pm_name, package_name)."""
    results: list[tuple[str, str]] = []
    q = query.lower()

    try:
        r = subprocess.run(
            ["dpkg", "--get-selections"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 1 and parts[0].lower().startswith(q):
                if len(parts) < 2 or parts[1] == "install":
                    results.append(("apt", parts[0]))
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["snap", "list"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines()[1:]:
            name = line.split()[0] if line.split() else ""
            if name and name.lower().startswith(q):
                results.append(("snap", name))
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            app = line.strip()
            if app:
                short_name = app.split('.')[-1].lower()
                if app.lower().startswith(q) or short_name.startswith(q):
                    results.append(("flatpak", app))
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for pm, name in results:
        key = f"{pm}:{name}"
        if key not in seen:
            seen.add(key)
            unique.append((pm, name))
    return sorted(unique, key=lambda x: (x[1].lower(), x[0]))


def remove_program_and_residuals() -> None:
    """
    Interactive deep-removal tool.
    Detects the package manager, checks reverse dependencies, lists residuals,
    then removes both the program and its leftover files — safely.
    """
    clear_screen()
    header("Program Deep Removal & Residual Purge")

    if not state.HAS_SUDO_PERM:
        center_print(f"{RED}  [✗] Error: Sudo privileges are required for this operation.{RESET}")
        wait_for_enter()
        return

    while True:
        clear_screen(); header("Program Deep Removal & Residual Purge")
        center_print(f"{YELLOW}  [?] Enter the program name (or partial name) to remove (or press Enter to cancel):{RESET}")
        c = cols()
        try:
            raw = input(" " * max(0, c // 2 - 3) + "  ➜  ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if not raw:
            center_print(f"{YELLOW}  [-] Cancelled.{RESET}")
            wait_for_enter()
            return

        if not re.match(r'^[a-z0-9][a-z0-9+\-._]*$', raw):
            center_print(f"{RED}  [✗] Invalid input: '{raw}'. Aborting.{RESET}")
            time.sleep(2)
            continue

        if len(raw) < 3:
            center_print(f"{RED}  [✗] Please type at least 3 characters.{RESET}")
            time.sleep(2)
            continue

        candidates = _search_packages(raw)

        if not candidates:
            center_print(f"{RED}  [✗] No installed packages match '{raw}'.{RESET}")
            time.sleep(2)
            continue

        break

    if len(candidates) == 1:
        pkg = candidates[0][1]
        center_print(f"  {GREEN}[✓]{RESET}  Found: {BOLD}{pkg}{RESET}")
        print()
    else:
        center_print(f"{YELLOW}  [!] Multiple packages matching '{raw}':{RESET}\n")
        for i, (pm, name) in enumerate(candidates, 1):
            center_print(f"  {GREEN}{BOLD}[{i}]{RESET}  {name:<35}  {DIM}({pm.upper()}){RESET}")
        print()
        center_print(f"  {RED}{BOLD}[0]{RESET}  Cancel")
        print()
        choice = ask_choice([str(i) for i in range(len(candidates) + 1)])
        if choice == "0":
            center_print(f"{YELLOW}  [-] Cancelled.{RESET}")
            wait_for_enter()
            return
        pkg = candidates[int(choice) - 1][1]
        print()
        center_print(f"  {GREEN}[✓]{RESET}  Selected: {BOLD}{pkg}{RESET}")
        print()

    if pkg in _CRITICAL_PACKAGES or any(pkg.startswith(cp) for cp in _CRITICAL_PACKAGES):
        center_print(f"{RED}  [✗] BLOCKED: '{pkg}' is a critical system package.{RESET}")
        center_print(f"{RED}       Removing it could render your system unbootable.{RESET}")
        wait_for_enter()
        return

    print()
    center_print(f"{CYAN}  [*] Analyzing '{pkg}'...{RESET}")
    print()

    pm = _detect_package_manager(pkg)
    if pm is None:
        center_print(f"{YELLOW}  [!] '{pkg}' is not installed via APT, Snap, or Flatpak.{RESET}")
        center_print(f"{DIM}       Proceeding to scan for residual files only...{RESET}")
        print()
    else:
        center_print(f"  {GREEN}[✓]{RESET}  Found via {BOLD}{pm.upper()}{RESET}")
        print()

    critical_rdeps: list[str] = []
    normal_rdeps:   list[str] = []
    if pm == "apt":
        center_print(f"{CYAN}  [*] Checking reverse dependencies...{RESET}")
        rdeps = _get_apt_reverse_deps(pkg)
        if rdeps:
            for dep in rdeps:
                if dep in _CRITICAL_PACKAGES or any(dep.startswith(cp) for cp in _CRITICAL_PACKAGES):
                    critical_rdeps.append(dep)
                else:
                    normal_rdeps.append(dep)

        if critical_rdeps:
            print()
            center_print(f"{RED}{BOLD}  [✗] HARD BLOCK: Removing '{pkg}' will break CRITICAL system packages:{RESET}")
            for dep in critical_rdeps:
                center_print(f"      {RED}→  {dep}{RESET}")
            center_print(f"{RED}       Operation aborted to protect system integrity.{RESET}")
            wait_for_enter()
            return

        if normal_rdeps:
            print()
            center_print(f"{YELLOW}{BOLD}  [!] WARNING: The following installed packages depend on '{pkg}':{RESET}")
            for dep in normal_rdeps[:20]:
                center_print(f"      {YELLOW}→  {dep}{RESET}")
            if len(normal_rdeps) > 20:
                center_print(f"      {DIM}... and {len(normal_rdeps) - 20} more{RESET}")
            print()
            center_print(f"{YELLOW}  [!] These packages may break or be removed alongside '{pkg}'.{RESET}")
            print()
            if not ask_yes_no(f"{RED}  [?] Proceed despite dependent packages?{RESET}", default_no=True):
                print()
                center_print(f"{YELLOW}  [-] Aborted: No changes made.{RESET}")
                wait_for_enter()
                return
        else:
            center_print(f"  {GREEN}[✓]{RESET}  No reverse dependencies found. Safe to remove.")
        print()

    center_print(f"{CYAN}  [*] Scanning for residual files and directories...{RESET}")
    print()
    residuals = _collect_residuals(pkg, pm=pm)

    if residuals:
        center_print(f"{YELLOW}  [!] Residual footprint found:{RESET}\n")
        total_res = 0
        for r in residuals:
            center_print(f"  {DIM}→{RESET}  {r['label']:<45}  {YELLOW}{r['size_fmt']}{RESET}")
            total_res += r["size_bytes"]
        print()
        _divider()
        center_print(f"  Total residual size:  {YELLOW}{BOLD}{format_size(total_res)}{RESET}")
        print()
    else:
        center_print(f"  {GREEN}[✓]{RESET}  No residual files found.")
        print()

    if pm is None and not residuals:
        center_print(f"{GREEN}  [✓] Nothing to remove. System is already clean.{RESET}")
        wait_for_enter()
        return

    if state.IS_DRY_RUN:
        center_print(f"{YELLOW}  [i] DRY RUN ACTIVE. No packages will be removed — simulation only.{RESET}")
    else:
        center_print(f"{RED}  [!] WARNING: PURGE IS PERMANENT.{RESET}")
    print()

    if pm is not None:
        prompt = f"Remove '{pkg}' via {pm.upper()} now?" if not state.IS_DRY_RUN else f"Simulate removal of '{pkg}'?"
        if ask_yes_no(f"{YELLOW}  [?] {prompt}{RESET}"):
            print()
            center_print(f"{CYAN}  [*] {'Removing' if not state.IS_DRY_RUN else 'Simulating removal of'} '{pkg}'...{RESET}\n")
            ok = False
            if pm == "apt":
                ok = _run(["apt-get", "purge", "-y", pkg], use_sudo=True)
                if ok:
                    _run(["apt-get", "autoremove", "-y"], use_sudo=True)
            elif pm == "snap":
                ok = _run(["snap", "remove", "--purge", pkg], use_sudo=True)
            elif pm == "flatpak":
                ok = _run(["flatpak", "uninstall", "-y", pkg], use_sudo=True)

            status = f"{GREEN}[✓]{RESET}" if ok else f"{RED}[✗]{RESET}"
            msg    = "removed successfully" if ok else "removal encountered an error"
            center_print(f"  {status}  '{pkg}' {msg}.")
            print()

            if residuals and ok:
                prompt_r = "Delete all residual files listed above?" if not state.IS_DRY_RUN else "Simulate residual deletion?"
                if ask_yes_no(f"{YELLOW}  [?] {prompt_r}{RESET}"):
                    print()
                    center_print(f"{CYAN}  [*] {'Purging' if not state.IS_DRY_RUN else 'Simulating purge of'} residual files...{RESET}\n")
                    for r in residuals:
                        ok = delete_path_content(r["path"], delete_root=True)
                        status = f"{GREEN}✓" if ok else f"{RED}✗"
                        center_print(f"    [{status}{RESET}]  {r['label']}")
                    print()
                    msg = "Residuals purged." if not state.IS_DRY_RUN else "Dry run complete. No residuals were removed."
                    center_print(f"{GREEN}  [✓] {msg}{RESET}")
                else:
                    print()
        else:
            print()
            center_print(f"{YELLOW}  [-] Package removal skipped.{RESET}")
            print()
            center_print(f"{YELLOW}  [-] Residual files preserved.{RESET}")

    elif residuals:
        prompt_r = "Delete all residual files listed above?" if not state.IS_DRY_RUN else "Simulate residual deletion?"
        if ask_yes_no(f"{YELLOW}  [?] {prompt_r}{RESET}"):
            print()
            center_print(f"{CYAN}  [*] {'Purging' if not state.IS_DRY_RUN else 'Simulating purge of'} residual files...{RESET}\n")
            for r in residuals:
                ok = delete_path_content(r["path"], delete_root=True)
                status = f"{GREEN}✓" if ok else f"{RED}✗"
                center_print(f"    [{status}{RESET}]  {r['label']}")
            print()
            msg = "Residuals purged." if not state.IS_DRY_RUN else "Dry run complete. No residuals were removed."
            center_print(f"{GREEN}  [✓] {msg}{RESET}")
        else:
            print()
            center_print(f"{YELLOW}  [-] Residual files preserved.{RESET}")

    wait_for_enter()
