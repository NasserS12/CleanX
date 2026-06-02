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
    bar = "═" * min(columns, 60)
    print(f"\n{CYAN}{bar.center(columns)}")
    print(f"{title.center(columns)}")
    print(f"{bar.center(columns)}{RESET}\n")

def app_logo():
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

def need_root():
    if os.getuid() != 0:
        print(f"{RED}[✘] Error: This command requires Root privileges (Sudo).{RESET}")
        return False
    return True

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

def get_dir_size(path):
    total_size = 0
    if os.path.exists(path):
        if os.path.isfile(path) or os.path.islink(path):
            try: return os.path.getsize(path)
            except: return 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp) and not os.path.islink(fp):
                    try: total_size += os.path.getsize(fp)
                    except: pass
    return total_size

def format_size(bytes_size):
    if bytes_size == 0: return "0.00 MB"
    mb = bytes_size / (1024 * 1024)
    if mb > 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"

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

def inspect_apt_cache():
    header("APT Package Cache Inspection")
    size = get_dir_size("/var/cache/apt/archives")
    print(f"  {CYAN}ℹ{RESET} Cache Path: /var/cache/apt/archives")
    print(f"  {YELLOW}⚠{RESET} Consumed Space: {format_size(size)}")

def inspect_snap_cache():
    header("Snap Package Cache Inspection")
    size = get_dir_size("/var/lib/snapd/cache")
    print(f"  {CYAN}ℹ{RESET} Cache Path: /var/lib/snapd/cache")
    print(f"  {YELLOW}⚠{RESET} Consumed Space: {format_size(size)}")

def inspect_journal():
    header("System Logs (systemd-journal) Inspection")
    size = get_dir_size("/var/log/journal")
    print(f"  {CYAN}ℹ{RESET} Logs Path: /var/log/journal")
    print(f"  {YELLOW}⚠{RESET} Consumed Space: {format_size(size)}")

def inspect_ram_cache():
    header("RAM Cache & Buffers Inspection")
    try:
        with open("/proc/meminfo", "r") as f:
            content = f.read()
        cached = int(re.search(r"Cached:\s+(\d+)", content).group(1)) * 1024
        buffers = int(re.search(r"Buffers:\s+(\d+)", content).group(1)) * 1024
        total = cached + buffers
        print(f"  {CYAN}ℹ{RESET} Current Memory Cache Allocation:")
        print(f"    ← Cached: {format_size(cached)}")
        print(f"    ← Buffers: {format_size(buffers)}")
        print(f"    ← Total Clearable RAM: {format_size(total)}")
    except:
        print(f"{RED}[✘] Failed to parse system memory metrics.{RESET}")

def inspect_user_cache():
    header("Human Users Cache (.cache) Inspection")
    users = get_all_human_users()
    for user, home in users:
        c_path = os.path.join(home, ".cache")
        size = get_dir_size(c_path)
        print(f"    ← User: {GREEN}{user}{RESET} ({home}) → Cache Size: {YELLOW}{format_size(size)}{RESET}")

def inspect_thumbnails():
    header("User Interface Image Thumbnails Inspection")
    users = get_all_human_users()
    for user, home in users:
        t_path = os.path.join(home, ".cache/thumbnails")
        size = get_dir_size(t_path)
        print(f"    ← User: {GREEN}{user}{RESET} → Thumbnail Size: {YELLOW}{format_size(size)}{RESET}")

def full_report():
    clear_screen()
    header("Comprehensive Ubuntu Cache Analytics Report")
    
    apt = get_dir_size("/var/cache/apt/archives")
    snap = get_dir_size("/var/lib/snapd/cache")
    journal = get_dir_size("/var/log/journal")
    
    total_users_cache = 0
    users = get_all_human_users()
    for u, home in users:
        total_users_cache += get_dir_size(os.path.join(home, ".cache"))

    print(f"  [1] APT Package Cache (System) : {YELLOW}{format_size(apt)}{RESET}")
    print(f"  [2] Snap Engine Cache (Apps)   : {YELLOW}{format_size(snap)}{RESET}")
    print(f"  [3] System Journals & Logs     : {YELLOW}{format_size(journal)}{RESET}")
    print(f"  [4] Total Active Users Cache   : {YELLOW}{format_size(total_users_cache)}{RESET}")
    print("-" * 60)
    grand_total = apt + snap + journal + total_users_cache
    print(f"  {GREEN}✔ Cumulative Detected Cache Footprint: {format_size(grand_total)}{RESET}")
    wait_for_enter()

def clean_apt_autoclean():
    if not need_root(): return
    header("Obsolete Package Archive Purge (APT Autoclean)")
    if get_confirmation(f"{RED}[?] Are you sure you want to purge old packages? (y/N): {RESET}"):
        print(f"{CYAN}[*] Running apt-get autoclean...{RESET}")
        subprocess.run(["sudo", "apt-get", "autoclean"], capture_output=True)
        print(f"{GREEN}[✓] Obsolete packages cleared successfully.{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_apt_full():
    if not need_root(): return
    header("Complete APT Repository Cache Purge")
    if get_confirmation(f"{RED}[?] Clear all local package archives and deb files? (y/N): {RESET}"):
        print(f"{CYAN}[*] Emptying /var/cache/apt/archives...{RESET}")
        subprocess.run(["sudo", "apt-get", "clean"], capture_output=True)
        subprocess.run(["sudo", "apt-get", "autoremove", "-y"], capture_output=True)
        print(f"{GREEN}[✓] Local APT repository cache reset to 0.00 MB.{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_snap_old():
    if not need_root(): return
    header("Disabled & Superseded Snap Package Version Cleanup")
    if get_confirmation(f"{RED}[?] Destroy legacy and deactivated snap tracking files? (y/N): {RESET}"):
        print(f"{CYAN}[*] Searching for inactive snap revisions...{RESET}")
        try:
            output = subprocess.check_output(["snap", "list", "--all"], text=True)
            for line in output.splitlines()[1:]:
                if "disabled" in line:
                    parts = line.split()
                    name = parts[0]
                    rev = parts[2]
                    print(f"    ← Purging: {name} (Revision {rev})")
                    subprocess.run(["sudo", "snap", "remove", name, f"--revision={rev}"], capture_output=True)
            print(f"{GREEN}[✓] Residual dead snap iterations removed.{RESET}")
        except Exception as e:
            print(f"{RED}[X] Failure parsing active snap database: {e}{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_journal(time_limit="1d"):
    if not need_root(): return
    header(f"System Journal Log Vacuuming ({time_limit} Restriction)")
    if get_confirmation(f"{RED}[?] Enforce journal vacuuming older than {time_limit}? (y/N): {RESET}"):
        print(f"{CYAN}[*] Invoking journalctl vacuum engine...{RESET}")
        subprocess.run(["sudo", "journalctl", f"--vacuum-time={time_limit}"], capture_output=True)
        print(f"{GREEN}[✓] Journal logs truncated to defined threshold.{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_ram_cache():
    if not need_root(): return
    header("Dynamic Memory Cache Release (Drop Caches)")
    if get_confirmation(f"{RED}[?] Signal kernel to drop buffered memory pages? (y/N): {RESET}"):
        print(f"{CYAN}[*] Flushing active filesystem filesystem buffers...{RESET}")
        try:
            subprocess.run(["sudo", "sync"], check=True)
            subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches", shell=True, capture_output=True)
            print(f"{GREEN}[✓] System RAM caching layers released safely.{RESET}")
        except Exception as e:
            print(f"{RED}[X] Dynamic optimization fault: {e}{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_user_cache_single():
    header("Isolated Individual User Space Cache Purge")
    users = get_all_human_users()
    print(f"{CYAN}Available Human Users On System:{RESET}")
    for idx, (user, home) in enumerate(users, 1):
        print(f"  [{idx}] {user} ({home})")
    
    flush_input()
    try:
        u_idx = input(f"\n{YELLOW}Select Target User Index: {RESET}").strip()
        idx_int = int(u_idx) - 1
        if 0 <= idx_int < len(users):
            target_user, target_home = users[idx_int]
            if get_confirmation(f"{RED}[?] Purge directory environment (.cache) for [{target_user}]? (y/N): {RESET}"):
                c_path = os.path.join(target_home, ".cache")
                delete_path_content(c_path)
                print(f"{GREEN}[✓] Targeted home cache wiped clean.{RESET}")
            else:
                print(f"{YELLOW}[-] Operation canceled.{RESET}")
        else:
            print(f"{RED}[!] Selection index range mismatch.{RESET}")
    except:
        print(f"{RED}[!] Non-integer input detected.{RESET}")
    wait_for_enter()

def clean_all_users_cache():
    header("Global All Users Cache Environment Purge")
    if get_confirmation(f"{RED}[?] Wipe caching structures for all active system accounts? (y/N): {RESET}"):
        users = get_all_human_users()
        for user, home in users:
            print(f"  {CYAN}[*]{RESET} Processing environment cleanup for: {user}")
            delete_path_content(os.path.join(home, ".cache"))
        print(f"{GREEN}[✓] Global user space profiles cleaned successfully.{RESET}")
    else:
        print(f"{YELLOW}[-] Operation canceled.{RESET}")
    wait_for_enter()

def clean_all_safe():
    if not need_root(): return
    clear_screen()
    header("CorE Suite Autonomous Automated Maintenance Routine")
    if get_confirmation(f"{RED}[?] Authorize global storage cleaning stack? (y/N): {RESET}"):
        print(f"\n{CYAN}[1/5] Erasing systemic package archives...{RESET}")
        subprocess.run(["sudo", "apt-get", "clean"], capture_output=True)
        subprocess.run(["sudo", "apt-get", "autoremove", "-y"], capture_output=True)
        
        print(f"{CYAN}[2/5] Compressing logging infrastructure logs...{RESET}")
        subprocess.run(["sudo", "journalctl", f"--vacuum-time=1d"], capture_output=True)
        
        print(f"{CYAN}[3/5] Cleaning image metadata footprints (Thumbnails)...{RESET}")
        users = get_all_human_users()
        for u, home in users:
            delete_path_content(os.path.join(home, ".cache/thumbnails"))
            
        print(f"{CYAN}[4/5] Instructing kernel memory cleanup layers...{RESET}")
        subprocess.run(["sudo", "sync"], check=True)
        subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches", shell=True, capture_output=True)
        
        print(f"{CYAN}[5/5] Purging volatile directory mounts (/tmp)...{RESET}")
        delete_path_content("/tmp")
        
        print(f"\n{GREEN}[✓] Global optimization tasks concluded successfully.{RESET}")
    else:
        print(f"{YELLOW}[-] Global automated routine aborted.{RESET}")
    wait_for_enter()

def request_initial_sudo():
    global HAS_SUDO_PERM
    clear_screen()
    app_logo()
    print(f"{CYAN}[+] INITIALIZATION OPTIONS:{RESET}\n")
    print(f"    To fully scan and purge system logs & package databases,")
    print(f"    root elevation privileges are highly recommended.")
    print("-" * 70)
    
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

def main_menu():
    request_initial_sudo()
    while True:
        clear_screen()
        app_logo()
        
        sudo_status_str = f"{GREEN}Sudo-Enabled{RESET}" if HAS_SUDO_PERM else f"{YELLOW}User-Only Mode{RESET}"
        print(f"{CYAN}[+] Inspection Tools [Status: {sudo_status_str}]:{RESET}")
        print(f"    {GREEN}[1]{RESET}  Full Diagnostic Report")
        print(f"    {GREEN}[2]{RESET}  Inspect APT Cache")
        print(f"    {GREEN}[3]{RESET}  Inspect Snap Engine Cache")
        print(f"    {GREEN}[4]{RESET}  Inspect System Log Journals")
        print(f"    {GREEN}[5]{RESET}  Inspect RAM Caches Allocation")
        print(f"    {GREEN}[6]{RESET}  Inspect Users Home Cache")
        print(f"    {GREEN}[7]{RESET}  Inspect Image Rendering Thumbnails")
        print(f"\n{CYAN}[+] Purge Engine Tools:{RESET}")
        print(f"    {GREEN}[11]{RESET} Clean APT Redundant Files (Autoclean)")
        print(f"    {GREEN}[12]{RESET} Wipe APT Local Archives Completely")
        print(f"    {GREEN}[13]{RESET} Remove Deactivated Snap Implementations")
        print(f"    {GREEN}[14]{RESET} Vacuum System Logs (Keep Last 24 Hours)")
        print(f"    {GREEN}[15]{RESET} Drop Virtual Memory Runtime Caches")
        print(f"    {GREEN}[21]{RESET} Clear Isolated User Cache Directory")
        print(f"    {GREEN}[22]{RESET} Clear Global Accounts Cache Profiles")
        print(f"    {GREEN}[30]{RESET} Execute Full Autonomous Optimization Routine")
        print(f"    {RED}[0]{RESET}  Terminate Diagnostic Engine Session")
        
        flush_input()
        choice = input(f"\n{YELLOW}Enter choice option selection: {RESET}").strip()
        
        if choice == "1": full_report()
        elif choice == "2": 
            if HAS_SUDO_PERM: clear_screen(); inspect_apt_cache(); wait_for_enter()
            else: print(f"{RED}[X] Sudo required.{RESET}"); time.sleep(1.2)
        elif choice == "3": 
            if HAS_SUDO_PERM: clear_screen(); inspect_snap_cache(); wait_for_enter()
            else: print(f"{RED}[X] Sudo required.{RESET}"); time.sleep(1.2)
        elif choice == "4": 
            if HAS_SUDO_PERM: clear_screen(); inspect_journal(); wait_for_enter()
            else: print(f"{RED}[X] Sudo required.{RESET}"); time.sleep(1.2)
        elif choice == "5": clear_screen(); inspect_ram_cache(); wait_for_enter()
        elif choice == "6": clear_screen(); inspect_user_cache(); wait_for_enter()
        elif choice == "7": clear_screen(); inspect_thumbnails(); wait_for_enter()
        elif choice == "11": clean_apt_autoclean()
        elif choice == "12": clean_apt_full()
        elif choice == "13": clean_snap_old()
        elif choice == "14": clean_journal("1d")
        elif choice == "15": clean_ram_cache()
        elif choice == "21": clean_user_cache_single()
        elif choice == "22": clean_all_users_cache()
        elif choice == "30": clean_all_safe()
        elif choice == "0":
            print(f"{GREEN}\n[✓] Session closed successfully. Goodbye!{RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}[!] Error: Invalid selection '{choice}'. Try again.{RESET}", end="", flush=True)
            time.sleep(1.2)
            print("\r\033[K", end="", flush=True)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{RED}[!] Execution runtime interrupted via Ctrl+C.{RESET}\n")
        sys.exit(0)