import os
import sys
import subprocess
import shutil
import time
from contextlib import contextmanager

# --- CONFIGURATION & COLORS ---
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

# متغير عالمي لتتبع هل تم الموافقة على السودو في البداية أم لا
HAS_SUDO_PERM = False

# --- PROTECTED TERMINAL CONTROL ---
@contextmanager
def terminal_echo_control(enable_echo=True):
    """تحكم صارم لمنع الحروف العشوائية من التشوه البصري للواجهة"""
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
    # إيقاف الـ Echo تماماً أثناء انتظار ضغط انتر لحماية الواجهة من تشويه المدخلات العشوائية
    with terminal_echo_control(enable_echo=False):
        while True:
            try:
                char = sys.stdin.read(1)
                if char in ['\n', '\r']:
                    break
            except (KeyboardInterrupt, EOFError):
                break

def header():
    columns = shutil.get_terminal_size().columns
    padding_logo = " " * max(0, (columns - 45) // 2)
    slogan = "Structural Cache Analytics & Storage Optimization Suite"
    credits = "(Developed by Nasser)"
    padding_slogan = " " * max(0, (columns - len(slogan)) // 2)
    padding_credits = " " * max(0, (columns - len(credits)) // 2)

    print(f"{RED}")
    print(f"{padding_logo}  ████████╗  ████████╗  ████████╗  ████████╗")
    print(f"{padding_logo}  ██╔═════╝  ██╔════██╗ ██╔════██╗ ██╔═════╝")
    print(f"{padding_logo}  ██║        ██║    ██║ ████████╔╝ ███████╗ ")
    print(f"{padding_logo}  ██║        ██║    ██║ ██╔════██╗ ██╔════╝ ")
    print(f"{padding_logo}  ╚████████╗ ╚████████╔╝ ██║    ██║ ████████╗")
    print(f"{padding_logo}   ╚═══════╝  ╚═══════╝  ╚═╝    ╚═╝ ╚═══════╝")
    print(f"{RESET}")
    
    print(f"{padding_slogan}{YELLOW}{slogan}{RESET}")
    print(f"{padding_credits}{WHITE}{credits}{RESET}")
    
    bar_width = min(columns, 70)
    bar = "-" * bar_width
    print(f"{RED}{bar.center(columns)}{RESET}\n")

# --- UTILS ---
def get_user_home():
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        try:
            import pwd
            return pwd.getpwnam(sudo_user).pw_dir
        except:
            return os.path.expanduser(f"~{sudo_user}")
    return os.path.expanduser("~")

def request_initial_sudo():
    """طلب صلاحيات السودو عند بدء التشغيل بناءً على اختيار المستخدم"""
    global HAS_SUDO_PERM
    clear_screen()
    header()
    print(f"{CYAN}[+] INITIALIZATION OPTIONS:{RESET}\n")
    print(f"    To fully scan and purge system logs & package databases,")
    print(f"    root elevation privileges are highly recommended.")
    print("-" * 70)
    
    # استخدام دالة التأكيد الصارمة
    if get_confirmation(f"{YELLOW}[?] Launch tool with Sudo privileges for deep scan? (y/N): {RESET}"):
        print(f"\n{CYAN}[*] Requesting authentication...{RESET}")
        has_sudo_cache = subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0
        if os.getuid() == 0 or has_sudo_cache:
            HAS_SUDO_PERM = True
            return
        try:
            result = subprocess.run(['sudo', '-v'], check=False)
            if result.returncode == 0:
                HAS_SUDO_PERM = True
                print(f"{GREEN}[✓] Authentication successful.{RESET}")
                time.sleep(0.8)
            else:
                HAS_SUDO_PERM = False
                print(f"{RED}[X] Authentication failed. Proceeding in User-Only mode.{RESET}")
                time.sleep(1.5)
        except:
            HAS_SUDO_PERM = False
    else:
        HAS_SUDO_PERM = False
        print(f"\n{YELLOW}[-] User-Only Mode selected. System paths will be locked.{RESET}")
        time.sleep(1.5)

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
                try:
                    total_size = os.path.getsize(path)
                except:
                    pass
            else:
                for dirpath, _, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp) and not os.path.islink(fp):
                            try:
                                total_size += os.path.getsize(fp)
                            except:
                                pass
        results[name] = {"path": path, "size": total_size, "exists": exists}
    return results

def format_size(bytes_size):
    mb = bytes_size / (1024 * 1024)
    if mb > 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"

def delete_path_content(path):
    if not os.path.exists(path):
        return
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

# --- USER CACHE MANAGEMENT ---
def manage_user_cache():
    clear_screen()
    header()
    print(f"{CYAN}[+] TARGETED USER CACHE SCAN (No Redundancy){RESET}\n")
    
    home = get_user_home()
    
    user_paths = {
        "User Core Cache (General)   ": os.path.join(home, ".cache"),
        "Snap Application Cache       ": os.path.join(home, "snap/common/.cache"),
        "User Command History Logs    ": os.path.join(home, ".bash_history")
    }
    
    scan_results = calculate_target_paths(user_paths)
    total_bytes = 0
    
    for name, info in scan_results.items():
        status_str = f"{YELLOW}{format_size(info['size'])}{RESET}" if info['exists'] else f"{RED}Not Found{RESET}"
        print(f"    → {name} : {status_str}")
        total_bytes += info['size']
        
    print("-" * 65)
    print(f"    Total User Cache Target Size: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print("-" * 65)

    if total_bytes > 0:
        if get_confirmation(f"{RED}[?] Proceed to clear the detected User cache? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Purging user cache paths...{RESET}")
            for name, info in scan_results.items():
                if info['exists'] and info['size'] > 0:
                    delete_path_content(info['path'])
            print(f"{GREEN}[✓] Success: User space cache has been completely cleared.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Action Canceled: User cache directories were left untouched.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: Targeted user cache is already 0.00 MB.{RESET}")
        
    wait_for_enter()

# --- SYSTEM CACHE MANAGEMENT ---
def manage_system_cache():
    clear_screen()
    header()
    print(f"{CYAN}[+] TARGETED SYSTEM CACHE SCAN (Engine Core Paths){RESET}\n")
    
    # حظر الفحص فوراً إذا تم رفض السودو في بداية تشغيل السكربت
    if not HAS_SUDO_PERM:
        print(f"{RED}[X] Access Denied: This utility is running in User-Only mode.{RESET}")
        print(f"{YELLOW}[!] System paths are locked because Sudo was not authorized at startup.{RESET}")
        print("-" * 65)
        wait_for_enter()
        return

    system_paths = {
        "Generic System & App Caches  ": "/var/cache",
        "APT Package Database Lists   ": "/var/lib/apt/lists",
        "System Log Rotations (Journal)": "/var/log/journal",
        "Temporary Runtime Files       ": "/tmp"
    }
    
    scan_results = calculate_target_paths(system_paths)
    total_bytes = 0
    
    for name, info in scan_results.items():
        status_str = f"{YELLOW}{format_size(info['size'])}{RESET}" if info['exists'] else f"{RED}Not Found{RESET}"
        print(f"    → {name} : {status_str}")
        total_bytes += info['size']
        
    print("-" * 65)
    print(f"    Total System Cache Target Size: {GREEN if total_bytes == 0 else YELLOW}{format_size(total_bytes)}{RESET}")
    print("-" * 65)

    if total_bytes > 0:
        if get_confirmation(f"{RED}[?] Proceed to clear System cache? (y/N): {RESET}"):
            print(f"\n{CYAN}[*] Executing system-wide package & log purge...{RESET}")
            try:
                subprocess.run(['sudo', 'apt-get', 'clean'], capture_output=True)
                subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'], capture_output=True)
                subprocess.run(['sudo', 'journalctl', '--vacuum-time=1d'], capture_output=True)
                
                delete_path_content("/tmp")
                delete_path_content("/var/cache")
                print(f"{GREEN}[✓] Success: System structural cache successfully purged.{RESET}")
            except Exception as e:
                print(f"{RED}[X] Error: Core system cleanup encountered a runtime error.{RESET}")
        else:
            print(f"\n{YELLOW}[-] Action Canceled: System deployment files were preserved.{RESET}")
    else:
        print(f"{GREEN}[✓] Clean: Structural system cache is already 0.00 MB.{RESET}")
        
    wait_for_enter()

# --- MAIN CONTROLLER MENU ---
def main_menu():
    # استدعاء دالة سؤال السودو الترحيبية مرة واحدة فقط عند بداية البرنامج
    request_initial_sudo()
    
    while True:
        clear_screen()
        header()
        
        # إظهار حالة الصلاحيات الحالية في القائمة لتبدو احترافية
        sudo_status_str = f"{GREEN}Sudo-Enabled{RESET}" if HAS_SUDO_PERM else f"{YELLOW}User-Only Mode{RESET}"
        print(f"{CYAN}[+] SELECT ADVANCED SCAN TARGET [Status: {sudo_status_str}]:{RESET}\n")
        print(f"    {GREEN}[1]{RESET} Scan & Clean User Cache Only (Targeted)")
        print(f"    {GREEN}[2]{RESET} Scan & Clean System Engine Cache " + (f"({GREEN}Available{RESET})" if HAS_SUDO_PERM else f"({RED}Locked{RESET})"))
        print(f"    {GREEN}[3]{RESET} Exit Terminal Program")
        
        flush_input()
        choice = input(f"\n{YELLOW}Enter choice (1-3): {RESET}").strip()
        
        if choice == "1":
            manage_user_cache()
        elif choice == "2":
            manage_system_cache()
        elif choice == "3":
            print(f"{GREEN}\n[✓] Secure Core Diagnostics Exited cleanly. Goodbye!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Error: Invalid selection '{choice}'. Please enter 1, 2, or 3.{RESET}", end="", flush=True)
            time.sleep(1.2)
            print("\r\033[K", end="", flush=True)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{RED}[!] Script terminated safely via Ctrl+C.{RESET}\n")
        sys.exit(0)