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
            time.sleep(0.8)
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

def delete_path_content(path):
    if not os.path.exists(path): return
    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
        else:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not os.path.islink(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.unlink(item_path)
    except:
        pass

def manage_integrated_user_cache():
    clear_screen()
    header("Targeted User Profile Cache Scanner")
    home = get_user_home()
    
    user_paths = {
        "User Core Cache (General)   ": os.path.join(home, ".cache"),
        "Snap Application Cache       ": os.path.join(home, "snap/common/.cache"),
        "User Command History Logs    ": os.path.join(home, ".bash_history")
    }
    
    print(f"{CYAN}[*] Scanning all user space cache frameworks...{RESET}\n")
    scan_results = calculate_target_paths(user_paths)
    total_bytes = 0
    
    for name, info in scan_results.items():
        status_str = f"{YELLOW}{format_size(info['size'])}{RESET}" if info['exists'] else f"{RED}Not Found{RESET}"
        print(f"    → {name} : {status_str}")
        total_bytes += info['size']
        
    print("-" * 65)
    print(f"    Aggregated User Target Footprint: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print("-" * 65)

    if total_bytes > 0:
        if get_confirmation(f"{RED}[?] Proceed to purge all displayed User caches? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Discarding profile footprints...{RESET}")
            for name, info in scan_results.items():
                if info['exists'] and info['size'] > 0:
                    delete_path_content(info['path'])
            print(f"{GREEN}[✓] Success: System user profile cache environment cleared.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: User cache deployment parameters left un-touched.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: User target directory structures are already pristine.{RESET}")
    wait_for_enter()

def manage_integrated_system_cache():
    clear_screen()
    header("Targeted System Engine Structural Cache Scanner")
    
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] Access Denied: Running in User-Only Mode.{RESET}")
        print(f"{YELLOW}[!] System core metrics are locked. Authorize Sudo on runtime initialization.{RESET}")
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
        if get_confirmation(f"{RED}[?] Purge all listed systemic core engines and cache layouts? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Executing deep deployment scrub routines...{RESET}")
            try:
                subprocess.run(['sudo', 'apt-get', 'clean'], capture_output=True)
                subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'], capture_output=True)
                subprocess.run(['sudo', 'journalctl', '--vacuum-time=1d'], capture_output=True)
                
                delete_path_content("/tmp")
                delete_path_content("/var/cache")
                print(f"{GREEN}[✓] Success: System structural caches purged successfully.{RESET}")
            except Exception as e:
                print(f"{RED}[X] Runtime Failure: Error executing structural system clean: {e}{RESET}")
        else:
            print(f"\n{YELLOW}[-] Aborted: Core system operational files preserved safely.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: Core systemic architecture has no accumulated files.{RESET}")
    wait_for_enter()

def manage_isolated_user_cache():
    clear_screen()
    header("Isolated Individual User Profile Purge")
    users = get_all_human_users()
    print(f"{CYAN}Registered Active Profiles On System:{RESET}")
    for idx, (user, home) in enumerate(users, 1):
        print(f"  [{idx}] User: {user.ljust(12)} Path: {home}")
    
    flush_input()
    try:
        u_idx = input(f"\n{YELLOW}Select target profile index number: {RESET}").strip()
        idx_int = int(u_idx) - 1
        if 0 <= idx_int < len(users):
            target_user, target_home = users[idx_int]
            c_path = os.path.join(target_home, ".cache")
            size = calculate_target_paths({"temp": c_path})["temp"]["size"]
            
            print(f"\n    → Targeted User  : {GREEN}{target_user}{RESET}")
            print(f"    → Footprint Size : {YELLOW}{format_size(size)}{RESET}")
            
            if size > 0:
                if get_confirmation(f"\n{RED}[?] Destroy isolated cache framework for [{target_user}]? (y/N): {RESET}"):
                    delete_path_content(c_path)
                    print(f"{GREEN}[✓] User space environment cleared successfully.{RESET}")
                else:
                    print(f"{YELLOW}[-] Operation aborted.{RESET}")
            else:
                print(f"{GREEN}[✓] Profile target cache is already empty.{RESET}")
        else:
            print(f"{RED}[!] Error: Profile out of bound bounds range.{RESET}")
    except:
        print(f"{RED}[!] Error: Invalid numeric profile selection index.{RESET}")
    wait_for_enter()

def clean_snap_old_versions():
    clear_screen()
    header("Deactivated & Redundant Snap Package Cleaner")
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] Sudo authorization required to parse snap infrastructure.{RESET}")
        wait_for_enter()
        return

    if get_confirmation(f"{RED}[?] Scan and destroy dead deactivated snap revisions? (y/N): {RESET}"):
        print(f"{CYAN}[*] Evaluating core snap layout array...{RESET}")
        try:
            output = subprocess.check_output(["snap", "list", "--all"], text=True)
            purged = False
            for line in output.splitlines()[1:]:
                if "disabled" in line:
                    parts = line.split()
                    name = parts[0]
                    rev = parts[2]
                    print(f"    ← Destroying Legacy Version: {name} [Rev: {rev}]")
                    subprocess.run(["sudo", "snap", "remove", name, f"--revision={rev}"], capture_output=True)
                    purged = True
            if purged:
                print(f"{GREEN}[✓] Redundant dead snap packages purged successfully.{RESET}")
            else:
                print(f"{GREEN}[✓] Pristine: No disabled snap packages found on system.{RESET}")
        except Exception as e:
            print(f"{RED}[X] Fault: Failed to query core snap runtime controller.{RESET}")
    else:
        print(f"{YELLOW}[-] Snap clean operation aborted.{RESET}")
    wait_for_enter()

def clean_all_safe_macro():
    clear_screen()
    header("CleanX Suite Sovereign Autonomous Global Optimization Routine")
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] High privilege execution denied. Sudo is required for Global Macro Routine.{RESET}")
        wait_for_enter()
        return

    if get_confirmation(f"{RED}[?] Authorize global storage cleaning stack? (y/N): {RESET}"):
        print(f"\n{CYAN}[1/5] Erasing systemic package archives (APT Clean)...{RESET}")
        subprocess.run(["sudo", "apt-get", "clean"], capture_output=True)
        subprocess.run(["sudo", "apt-get", "autoremove", "-y"], capture_output=True)
        
        print(f"{CYAN}[2/5] Compressing logging infrastructure (Journal Vacuum)...{RESET}")
        subprocess.run(["sudo", "journalctl", f"--vacuum-time=1d"], capture_output=True)
        
        print(f"{CYAN}[3/5] Cleaning rendering engine metadata (Thumbnails)...{RESET}")
        users = get_all_human_users()
        for u, home in users:
            delete_path_content(os.path.join(home, ".cache/thumbnails"))
            
        print(f"{CYAN}[4/5] Instructing kernel memory virtual pages (Drop Caches)...{RESET}")
        subprocess.run(["sudo", "sync"], check=True)
        subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches", shell=True, capture_output=True)
        
        print(f"{CYAN}[5/5] Purging volatile directory mounts (/tmp)...{RESET}")
        delete_path_content("/tmp")
        
        print(f"\n{GREEN}[✓] Core Sovereign automation stack concluded execution successfully.{RESET}")
    else:
        print(f"{YELLOW}[-] Global macro optimization stack routine aborted.{RESET}")
    wait_for_enter()

def request_initial_sudo():
    global HAS_SUDO_PERM
    clear_screen()
    app_logo()
    print(f"{CYAN}[+] SECURITY INITIALIZATION OPTIONS:{RESET}\n")
    print(f"    To fully inspect and purge systemic engines, journaling metrics,")
    print(f"    and package list layout archives, root execution privileges are recommended.")
    print("-" * 75)
    
    if get_confirmation(f"{YELLOW}[?] Elevate runtime session to Sudo for deep scanning? (y/N): {RESET}"):
        print(f"\n{CYAN}[*] Interrogating privilege stack...{RESET}")
        has_sudo_cache = subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0
        if os.getuid() == 0 or has_sudo_cache:
            HAS_SUDO_PERM = True
            return
        try:
            result = subprocess.run(['sudo', '-v'], check=False)
            if result.returncode == 0:
                HAS_SUDO_PERM = True
                print(f"{GREEN}[✓] Authentication successful. High-privilege mode active.{RESET}")
                time.sleep(0.8)
            else:
                HAS_SUDO_PERM = False
                print(f"{RED}[X] Authentication failed. Dropping back to User-Only mode.{RESET}")
                time.sleep(1.5)
        except:
            HAS_SUDO_PERM = False
    else:
        HAS_SUDO_PERM = False
        print(f"\n{YELLOW}[-] Restricted execution authorized. Systemic pathways are locked.{RESET}")
        time.sleep(1.5)

def main_menu():
    request_initial_sudo()
    while True:
        clear_screen()
        app_logo()
        
        sudo_status_str = f"{GREEN}Sudo-Privileged{RESET}" if HAS_SUDO_PERM else f"{YELLOW}User-Restricted{RESET}"
        print(f"{CYAN}[+] CONSOLIDATED OPTIMIZATION INTERFACES [Status: {sudo_status_str}]:{RESET}\n")
        print(f"    {GREEN}[1]{RESET} Integrated Scan & Purge: User Profile Cache Environment")
        print(f"    {GREEN}[2]{RESET} Integrated Scan & Purge: System Engine Core Cache " + (f"({GREEN}Unlocked{RESET})" if HAS_SUDO_PERM else f"({RED}Locked{RESET})"))
        print(f"    {GREEN}[3]{RESET} Isolated Purge: Target Specific User Account Space")
        print(f"    {GREEN}[4]{RESET} Architectural Scrub: Remove Legacy Superseded Snap Revisions")
        print(f"    {GREEN}[5]{RESET} Sovereign Automation: Trigger Global Clean All Safe Macro Routine")
        print(f"    {RED}[0]{RESET} Terminate CleanX Optimization Session")
        
        flush_input()
        choice = input(f"\n{YELLOW}Select operation index identifier: {RESET}").strip()
        
        if choice == "1": manage_integrated_user_cache()
        elif choice == "2": manage_integrated_system_cache()
        elif choice == "3": manage_isolated_user_cache()
        elif choice == "4": clean_snap_old_versions()
        elif choice == "5": clean_all_safe_macro()
        elif choice == "0":
            print(f"{GREEN}\n[✓] Diagnostic optimization session exited cleanly. Goodbye Nasser!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Operational mismatch: '{choice}' is not valid. Re-trying...{RESET}", end="", flush=True)
            time.sleep(1.2)
            print("\r\033[K", end="", flush=True)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{RED}[!] Operational interruption caught via hardware signal. Terminating...{RESET}\n")
        sys.exit(0)