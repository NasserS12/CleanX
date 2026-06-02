import os
import sys
import subprocess
import shutil
import time
import re
from contextlib import contextmanager

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

HAS_SUDO_PERM = False

@contextmanager
def terminal_echo_control(enable_echo=True):
    if os.name == 'posix':
        import termios
        fd = sys.stdin.fileno()
        old_attr = termios.tcgetattr(fd)
        new_attr = termios.tcgetattr(fd)
        if not enable_echo:
            new_attr[3] = new_attr[3] & ~termios.ECHO
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, new_attr)
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
    else:
        yield

def clear_screen():
    print("\033[H\033[2J\033[3J", end="", flush=True)

def flush_input():
    if os.name == 'posix':
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass

def wait_for_enter():
    flush_input()
    print(f"\n{YELLOW}Press [Enter] to return to menu...{RESET}", end="", flush=True)
    with terminal_echo_control(enable_echo=False):
        while True:
            try:
                char = sys.stdin.read(1)
                if char in ['\n', '\r']:
                    break
            except (KeyboardInterrupt, EOFError):
                break

def header(title):
    columns = shutil.get_terminal_size().columns
    bar = "═" * min(columns, 65)
    print(f"\n{CYAN}{bar.center(columns)}")
    print(f"{title.center(columns)}")
    print(f"{bar.center(columns)}{RESET}\n")

def app_logo():
    columns = shutil.get_terminal_size().columns
    
    logo_cleanx = [
        " ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██╗  ██╗",
        "██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║╚██╗██╔╝",
        "██║     ██║     █████╗  ███████║██╔██╗ ██║ ╚███╔╝ ",
        "██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║ ██╔██╗ ",
        "╚██████╗███████╗███████╗██║  ██║██║ ╚████║██╔╝ ██╗",
        " ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"
    ]
    
    logo_sweeper = [
        "      ___          ",
        "     /  /\\         ",
        "    /  /::\\        ",
        "   /  /:/\\:\\       ",
        "  /  /:/  \\:\\      ",
        " /__/:/ \\__\\:\\     ",
        " \\  \\:\\ /  /:/   ==[ SYSTEM PURGE ENGINE ]==",
        "  \\  \\:\\  /:/    ==[ DISK OPTIMIZER      ]==",
        "   \\  \\:\\/:/       ",
        "    \\  \\::/        ",
        "     \\__\\/         "
    ]
    
    print(f"{RED}")
    for line in logo_cleanx:
        print(line.center(columns))
    print(f"{RESET}")
    
    print(f"{CYAN}")
    for line in logo_sweeper:
        print(line.center(columns))
    print(f"{RESET}")
    
    slogan = "⚡ Advanced Architectural Cache Analytics & Storage Scrub Suite ⚡"
    credits = "🛡️ [ Crafted Control Logical Framework by Nasser ] 🛡️"
    padding_slogan = " " * max(0, (columns - len(slogan)) // 2)
    padding_credits = " " * max(0, (columns - len(credits)) // 2)

    print(f"{padding_slogan}{YELLOW}{slogan}{RESET}")
    print(f"{padding_credits}{WHITE}{credits}{RESET}")
    
    bar_width = min(columns, 75)
    bar = "─" * bar_width
    print(f"{RED}{bar.center(columns)}{RESET}\n")

def get_confirmation(prompt_text):
    while True:
        flush_input()
        try:
            ans = input(prompt_text).lower().strip()
            if ans in ['y', 'yes', '1']:
                return True
            if ans in ['n', 'no', '0', '']:
                return False
            print(f"{RED}  [!] Invalid input. Use (y) or (n).{RESET}", end="", flush=True)
            time.sleep(1.8)
            print("\r\033[K\033[A\r\033[K", end="", flush=True)
        except (KeyboardInterrupt, EOFError):
            return False

def calculate_target_paths(paths_dict):
    results = {}
    for name, path in paths_dict.items():
        total_size = 0
        exists = os.path.exists(path)
        if exists:
            if os.path.isfile(path) or os.path.islink(path):
                try: total_size = os.path.getsize(path)
                except: pass
            else:
                for dirpath, _, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp) and not os.path.islink(fp):
                            try: total_size += os.path.getsize(fp)
                            except: pass
        results[name] = {"path": path, "size": total_size, "exists": exists}
    return results

def format_size(bytes_size):
    if bytes_size == 0: return "0.00 MB"
    kb = bytes_size / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"

def get_user_home():
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        try:
            import pwd
            return pwd.getpwnam(sudo_user).pw_dir
        except:
            return os.path.expanduser(f"~{sudo_user}")
    return os.path.expanduser("~")

def get_all_human_users():
    users = []
    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) >= 6:
                    uid = int(parts[2])
                    home = parts[5]
                    if (uid >= 1000 and uid != 65534) or uid == 0:
                        if os.path.exists(home):
                            users.append((parts[0], home))
    except:
        pass
    return users

def delete_path_content(path, delete_root=False):
    if not os.path.exists(path): return
    use_sudo = check_sudo_status()
    try:
        if os.path.isfile(path) or os.path.islink(path):
            if use_sudo: subprocess.run(['sudo', 'rm', '-f', path], capture_output=True)
            else: os.unlink(path)
        elif delete_root:
            if use_sudo: subprocess.run(['sudo', 'rm', '-rf', path], capture_output=True)
            else: shutil.rmtree(path)
        else:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not os.path.islink(item_path):
                    if use_sudo: subprocess.run(['sudo', 'rm', '-rf', item_path], capture_output=True)
                    else: shutil.rmtree(item_path)
                else:
                    if use_sudo: subprocess.run(['sudo', 'rm', '-f', item_path], capture_output=True)
                    else: os.unlink(item_path)
    except:
        pass

def find_recursive_targets(root_dir, target_name):
    paths = []
    total_size = 0
    skip_dirs = {
        '.cache', '.local', '.git', 'venv', 'node_modules', 
        'Downloads', 'Pictures', 'Videos', 'Music', 'Desktop',
        '.cargo', '.rustup', '.npm', '.nvm', '.vscode', '.idea'
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        if target_name in dirnames:
            p = os.path.join(dirpath, target_name)
            paths.append(p)
            for dp, _, fns in os.walk(p):
                for f in fns:
                    fp = os.path.join(dp, f)
                    try: 
                        if not os.path.islink(fp):
                            total_size += os.path.getsize(fp)
                    except: pass
    return paths, total_size

def manage_integrated_user_cache():
    clear_screen()
    header("User Profile Cache Cleanup")
    home = get_user_home()
    
    user_paths = {
        "User Core Cache (General)   ": os.path.join(home, ".cache"),
        "User Temporary Staging (tmp)": os.path.join(home, "tmp"),
        "Snap Application Cache       ": os.path.join(home, "snap/common/.cache"),
        "User Command History Logs    ": os.path.join(home, ".bash_history")
    }
    
    print(f"{CYAN}[*] Initiating comprehensive user profile scan...{RESET}\n")
    scan_results = calculate_target_paths(user_paths)
    
    pycache_paths, pycache_size = find_recursive_targets(home, "__pycache__")
    scan_results["Python Bytecode (__pycache__)"] = {
        "path": pycache_paths,
        "size": pycache_size,
        "exists": len(pycache_paths) > 0,
        "is_recursive": True
    }
    
    total_bytes = 0
    has_any_exists = False
    for name, info in scan_results.items():
        status_str = f"{YELLOW}{format_size(info['size'])}{RESET}" if info['exists'] else f"{RED}Not Found{RESET}"
        print(f"    → {name.ljust(32)} : {status_str}")
        total_bytes += info['size']
        if info['exists']: has_any_exists = True
        
    print("-" * 65)
    print(f"    Aggregated User Target Footprint: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print("-" * 65)

    if has_any_exists:
        print(f"\n{RED}    [!] WARNING: Purge is PERMANENT. Files will NOT go to Trash.{RESET}")
        if get_confirmation(f"{YELLOW}    [?] Proceed to destroy all displayed user targets? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Discarding profile footprints...{RESET}")
            for name, info in scan_results.items():
                if info['exists']:
                    targets = info['path'] if isinstance(info['path'], list) else [info['path']]
                    is_pycache = info.get("is_recursive", False)
                    for t in targets:
                        delete_path_content(t, delete_root=is_pycache)
            print(f"{GREEN}[✓] Success: System user profile environment optimized.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: User profile parameters left un-touched.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: User target directory structures are already pristine.{RESET}")
    wait_for_enter()

def manage_integrated_system_cache():
    clear_screen()
    header("System Engine Core Cleanup")
    
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] Access Denied: Running in User-Only Mode.{RESET}")
        print("-" * 65)
        wait_for_enter()
        return

    system_paths = {
        "Generic System & App Caches  ": "/var/cache",
        "APT Package Database Lists   ": "/var/lib/apt/lists",
        "System Log Rotations (Journal)": "/var/log/journal",
        "Temporary Runtime Files       ": "/tmp"
    }
    
    print(f"{CYAN}[*] Scanning architectural kernel & package caches...{RESET}\n")
    scan_results = calculate_target_paths(system_paths)
    total_bytes = 0
    
    for name, info in scan_results.items():
        status_str = f"{YELLOW}{format_size(info['size'])}{RESET}" if info['exists'] else f"{RED}Not Found{RESET}"
        print(f"    → {name} : {status_str}")
        total_bytes += info['size']
        
    print("-" * 65)
    print(f"    Aggregated System Target Footprint: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print("-" * 65)

    if total_bytes > 0:
        print(f"\n{RED}    [!] WARNING: Purge is PERMANENT. System files will be lost.{RESET}")
        if get_confirmation(f"{YELLOW}    [?] Purge all listed systemic core engines and cache layouts? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Executing deep deployment scrub routines...{RESET}")
            try:
                subprocess.run(['sudo', 'apt-get', 'clean'], capture_output=True)
                subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'], capture_output=True)
                subprocess.run(['sudo', 'journalctl', '--vacuum-time=1d'], capture_output=True)
                
                delete_path_content("/tmp", delete_root=False)
                delete_path_content("/var/cache", delete_root=False)
                print(f"{GREEN}[✓] Success: System structural caches purged successfully.{RESET}")
            except Exception as e:
                print(f"{RED}[X] Runtime Failure: Error executing structural system clean: {e}{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: Core system operational files preserved safely.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: Core systemic architecture has no accumulated files.{RESET}")
    wait_for_enter()

def clean_snap_old_versions():
    clear_screen()
    header("Redundant Snap Package Version Removal")
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] Sudo authorization required to parse snap infrastructure.{RESET}")
        wait_for_enter()
        return

    print(f"{CYAN}[*] Investigating core snap layout array...{RESET}\n")
    try:
        output = subprocess.check_output(["snap", "list", "--all"], text=True)
        dead_snaps = []
        for line in output.splitlines()[1:]:
            if re.search(r'\bdisabled\b', line, re.IGNORECASE):
                parts = re.split(r'\s{2,}', line.strip())
                if not parts: parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    rev = parts[2]
                    if not rev.isdigit() and len(parts) > 3: rev = parts[3]
                    dead_snaps.append((name, rev))
        
        if not dead_snaps:
            print(f"{GREEN}[✓] Pristine: No disabled or legacy snap packages found.{RESET}")
            wait_for_enter()
            return

        print(f"{YELLOW}[!] Discovered {len(dead_snaps)} redundant snap versions:{RESET}")
        for name, rev in dead_snaps:
            print(f"    → {name.ljust(20)} [Revision: {rev}]")
        
        print(f"\n{RED}    [!] WARNING: Removed snap versions cannot be restored.{RESET}")
        if get_confirmation(f"{YELLOW}    [?] Proceed to destroy all redundant snap revisions? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Purging deactivated revisions...{RESET}")
            for name, rev in dead_snaps:
                print(f"    ← Destroying: {name} ({rev})")
                subprocess.run(["sudo", "snap", "remove", name, f"--revision={rev}"], capture_output=True)
            print(f"\n{GREEN}[✓] Success: Redundant snap infrastructure cleared.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: Redundant snap versions preserved.{RESET}")
    except Exception as e:
        print(f"{RED}[X] Fault: Failed to query core snap runtime controller: {e}{RESET}")
    
    wait_for_enter()

def clean_all_safe_macro():
    clear_screen()
    header("Sovereign Mode: Full System Optimization")
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] High privilege execution denied. Sudo is required for Sovereign Macro.{RESET}")
        wait_for_enter()
        return

    print(f"{CYAN}[*] Running architectural global scan...{RESET}\n")
    
    # 1. Scan Paths
    sys_paths = {
        "APT Package Archive Cache      ": "/var/cache/apt/archives",
        "System Engine Journal Logs     ": "/var/log/journal",
        "Volatile Boot Staging (/tmp)   ": "/tmp"
    }
    
    results = calculate_target_paths(sys_paths)
    
    # 2. Add Users Thumbnails size
    thumbnail_size = 0
    all_users = get_all_human_users()
    thumbnail_paths = []
    for _, home in all_users:
        tp = os.path.join(home, ".cache/thumbnails")
        if os.path.exists(tp):
            thumbnail_paths.append(tp)
            for dp, _, fns in os.walk(tp):
                for f in fns:
                    fp = os.path.join(dp, f)
                    try: 
                        if not os.path.islink(fp): thumbnail_size += os.path.getsize(fp)
                    except: pass

    results["Global User Thumbnail Cache   "] = {"size": thumbnail_size, "exists": thumbnail_size > 0}

    # Display results
    total_bytes = 0
    for name, info in results.items():
        status = f"{YELLOW}{format_size(info['size'])}{RESET}" if info.get('exists', True) else f"{RED}Not Found{RESET}"
        print(f"    → {name} : {status}")
        total_bytes += info['size']

    print("-" * 65)
    print(f"    Aggregated Sovereign Footprint: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print(f"    Note: Kernel RAM optimization (Drop Caches) is also queued.")
    print("-" * 65)

    if total_bytes > 0:
        print(f"\n{RED}    [!] CRITICAL: This will PERMANENTLY delete all listed items.{RESET}")
        if get_confirmation(f"{YELLOW}    [?] Authorize global storage cleaning stack? (y/N): {RESET}"):
            print(f"\n{CYAN}[1/5] Erasing systemic package archives (APT Clean)...{RESET}")
            subprocess.run(["sudo", "apt-get", "clean"], capture_output=True)
            subprocess.run(["sudo", "apt-get", "autoremove", "-y"], capture_output=True)
            
            print(f"{CYAN}[2/5] Compressing logging infrastructure (Journal Vacuum)...{RESET}")
            subprocess.run(["sudo", "journalctl", f"--vacuum-time=1d"], capture_output=True)
            
            print(f"{CYAN}[3/5] Cleaning rendering engine metadata (Thumbnails)...{RESET}")
            for tp in thumbnail_paths:
                delete_path_content(tp, delete_root=True)
                
            print(f"{CYAN}[4/5] Instructing kernel memory virtual pages (Drop Caches)...{RESET}")
            subprocess.run(["sudo", "sync"], check=True)
            subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches", shell=True, capture_output=True)
            
            print(f"{CYAN}[5/5] Purging volatile directory mounts (/tmp)...{RESET}")
            delete_path_content("/tmp", delete_root=False)
            
            print(f"\n{GREEN}[✓] Core Sovereign automation stack concluded execution successfully.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: Global macro optimization stack routine aborted.{RESET}")
    else:
        print(f"{GREEN}[✓] Pristine: No systemic junk found during Sovereign scan.{RESET}")
    
    wait_for_enter()

def check_sudo_status():
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0

def attempt_elevation(show_logo=False):
    global HAS_SUDO_PERM
    if show_logo:
        clear_screen()
        app_logo()
        print(f"{CYAN}[+] SECURITY INITIALIZATION OPTIONS:{RESET}\n")
        print(f"    To fully inspect and purge systemic engines, journaling metrics,")
        print(f"    and package list layout archives, root execution privileges are recommended.")
        print("-" * 75)

    if not show_logo or get_confirmation(f"{YELLOW}[?] Elevate runtime session to Sudo for deep scanning? (y/N): {RESET}"):
        print(f"\n{CYAN}[*] Interrogating privilege stack...{RESET}")
        try:
            result = subprocess.run(['sudo', '-v'], check=False)
            if result.returncode == 0:
                HAS_SUDO_PERM = True
                print(f"{GREEN}[✓] Authentication successful. High-privilege mode active.{RESET}")
                time.sleep(2.0)
                return True
            else:
                HAS_SUDO_PERM = False
                print(f"{RED}[X] Authentication failed. Dropping back to User-Only mode.{RESET}")
                time.sleep(2.5)
                return False
        except:
            HAS_SUDO_PERM = False
            return False
    else:
        HAS_SUDO_PERM = False
        if show_logo:
            print(f"\n{YELLOW}[-] Restricted execution authorized. Systemic pathways are locked.{RESET}")
            time.sleep(2.5)
    return False

def main_menu():
    global HAS_SUDO_PERM
    # Initial check & startup prompt
    if check_sudo_status() or os.getuid() == 0:
        HAS_SUDO_PERM = True
        clear_screen()
        app_logo()
        print(f"{GREEN}[✓] Existing privilege session detected. Sudo mode enabled.{RESET}")
        time.sleep(1.5)
    else:
        attempt_elevation(show_logo=True)

    while True:
        # Sync status with terminal cache
        if not HAS_SUDO_PERM:
            if check_sudo_status(): HAS_SUDO_PERM = True
        else:
            if not check_sudo_status() and os.getuid() != 0: HAS_SUDO_PERM = False

        clear_screen()
        app_logo()
        
        sudo_status_str = f"{GREEN}Sudo-Privileged{RESET}" if HAS_SUDO_PERM else f"{YELLOW}User-Restricted{RESET}"
        print(f"{CYAN}[+] CONSOLIDATED OPTIMIZATION INTERFACES [Status: {sudo_status_str}]:{RESET}\n")
        print(f"    {GREEN}[1]{RESET} User Profile Cache Cleanup (Scan & Purge)")
        print(f"    {GREEN}[2]{RESET} System Engine Core Cleanup (Logs & APT) " + (f"({GREEN}Unlocked{RESET})" if HAS_SUDO_PERM else f"({RED}Locked{RESET})"))
        print(f"    {GREEN}[3]{RESET} Redundant Snap Package Version Removal " + (f"({GREEN}Unlocked{RESET})" if HAS_SUDO_PERM else f"({RED}Locked{RESET})"))
        print(f"    {GREEN}[4]{RESET} Full System Optimization Macro (Sovereign Mode) " + (f"({GREEN}Unlocked{RESET})" if HAS_SUDO_PERM else f"({RED}Locked{RESET})"))
        print(f"    {RED}[0]{RESET} Exit CleanX Optimization Session")
        
        flush_input()
        choice = input(f"\n{YELLOW}Select operation index identifier: {RESET}").strip()
        
        if choice == "1": manage_integrated_user_cache()
        elif choice in ["2", "3", "4"]:
            if not HAS_SUDO_PERM:
                if get_confirmation(f"{YELLOW}[?] This option is Locked. Elevate to Sudo now? (y/N): {RESET}"):
                    if not attempt_elevation(show_logo=False): continue
            
            if choice == "2": manage_integrated_system_cache()
            elif choice == "3": clean_snap_old_versions()
            elif choice == "4": clean_all_safe_macro()
        elif choice == "0":
            print(f"{GREEN}\n[✓] Diagnostic optimization session exited cleanly. Goodbye Nasser!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Operational mismatch: '{choice}' is not valid. Re-trying...{RESET}", end="", flush=True)
            time.sleep(2.5)
            print("\r\033[K", end="", flush=True)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{RED}[!] Operational interruption caught via hardware signal. Terminating...{RESET}\n")
        sys.exit(0)
