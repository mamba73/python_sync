import xml.etree.ElementTree as ET
import subprocess
import sys
import argparse
import re
import os
import configparser
import shutil
import zipfile
from datetime import datetime, timedelta

# ==============================================================================
# VERSION & METADATA
# ==============================================================================
SCRIPT_VER = "1.9.5"

# --- PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "config_sync.ini")

# ==============================================================================
# SMART CONFIGURATION SYSTEM
# ==============================================================================
def load_and_sync_config():
    config = configparser.ConfigParser()
    detected_folder = os.path.basename(os.getcwd())
    
    defaults = {
        'LocalFolderName': 'CHANGE_ME',
        'RemoteProjectName': detected_folder,
        'DefaultVersion': '1.0.0',
        'DevRemote': 'origin',
        'ReleaseRemote': 'origin',
        'DevBranch': 'dev',
        'ReleaseBranch': 'master',
        'ManifestPath': 'manifest.xml',
        'ReadmePath': 'README.md',
        'ChangelogPath': 'CHANGELOG.md',
        'LogDir': 'logs',
        'KeepLogsDays': '7',
        'MaxZipSizeMB': '100',
        'VSCodePath': r"c:\dev\VSCode\bin\code.cmd",
        'ReleaseWhiteList': r'Plugin/, manifest.xml, .gitignore, LICENSE, CHANGELOG.md, .*\.csproj$, .*\.sln$, .*\.md$',
        'BackupFormat': '{date}_{time}_{type}_{project}_v{version}_{remote}_{branch}.zip'
    }
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if 'SETTINGS' not in config:
        config['SETTINGS'] = {}

    updated = False
    for key, value in defaults.items():
        if not config.has_option('SETTINGS', key):
            config.set('SETTINGS', key, value)
            updated = True

    if config.get('SETTINGS', 'LocalFolderName') == 'CHANGE_ME':
        if len(sys.argv) > 1 and sys.argv in ['-h', '--help']:
            return config['SETTINGS']
            
        print(f"\n--- MAMBA SYNC TOOL SETUP ---")
        print(f"Detected current directory: {detected_folder}")
        confirm = input(f"Use '{detected_folder}' as the Project Root Folder? (y/n): ").lower()
        
        if confirm == 'y':
            config.set('SETTINGS', 'LocalFolderName', detected_folder)
            updated = True
        else:
            custom_name = input("Enter the EXACT name of your project root folder: ").strip()
            if custom_name:
                config.set('SETTINGS', 'LocalFolderName', custom_name)
                updated = True
            else:
                sys.exit("[FATAL] Project folder name is required.")

    if updated:
        with open(config_file, 'w') as f:
            config.write(f)

    return config['SETTINGS']

cfg = load_and_sync_config()

# Global Mapping
DEV_BRANCH = cfg.get('DevBranch')
RELEASE_BRANCH = cfg.get('ReleaseBranch')
MANIFEST_PATH = cfg.get('ManifestPath')
README_PATH = cfg.get('ReadmePath')
CHANGELOG_PATH = cfg.get('ChangelogPath')
LOG_DIR = os.path.join(script_dir, cfg.get('LogDir'))
VS_CODE_PATH = cfg.get('VSCodePath')
RELEASE_WHITELIST = [item.strip() for item in cfg.get('ReleaseWhiteList').split(',')]
BACKUP_NAME_FORMAT = cfg.get('BackupFormat')
PROJECT_NAME = cfg.get('RemoteProjectName')

# ==============================================================================
# VERSION SYSTEM
# ==============================================================================
def auto_increment_version(current):
    try:
        parts = current.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    except: return current

def get_project_version(auto_yes=False):
    current_ver = cfg.get('DefaultVersion', '1.0.0')
    if os.path.exists(MANIFEST_PATH):
        try:
            tree = ET.parse(MANIFEST_PATH)
            node = tree.getroot().find('Version')
            if node is not None: current_ver = node.text.strip()
        except: pass
    elif os.path.exists(README_PATH):
        try:
            with open(README_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r"(?i)\*?\*?version\*?\*?[:\s]+([0-9\.]+)", content)
                if match: current_ver = match.group(1)
        except: pass

    if auto_yes:
        new_ver = auto_increment_version(current_ver)
    else:
        print(f"\nCurrent version: {current_ver}")
        suggested = auto_increment_version(current_ver)
        user_input = input(f"Enter new version [{suggested}] (Enter to confirm): ").strip()
        new_ver = user_input if user_input else suggested

    config = configparser.ConfigParser()
    config.read(config_file)
    config.set('SETTINGS', 'DefaultVersion', new_ver)
    with open(config_file, 'w') as f: config.write(f)
    return new_ver

# ==============================================================================
# UTILITIES
# ==============================================================================
def log_and_print(message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level}] {message}"
    print(formatted)
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f: f.write(formatted + "\n")
    except: pass

def check_run(cmd, exit_on_fail=True):
    log_and_print(f"EXECUTING: {cmd}", "DEBUG")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        log_and_print(f"FAILED: {res.stderr.strip()}", "ERROR")
        if exit_on_fail: sys.exit(1)
        return None
    return res.stdout.strip() if res.stdout else "SUCCESS"

def get_current_branch():
    return subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, text=True, capture_output=True).stdout.strip()

# ==============================================================================
# ENHANCED BACKUP SYSTEM (FIXED WHITELIST)
# ==============================================================================
def create_backup(version, type_label, destination="parent"):
    name = BACKUP_NAME_FORMAT.format(
        date=datetime.now().strftime("%Y-%m-%d"), 
        time=datetime.now().strftime("%H%M%S"), 
        type=type_label, 
        project=PROJECT_NAME,
        remote="LOCAL", 
        version=version, 
        branch=get_current_branch()
    )
    
    base_target_dir = os.path.abspath(os.path.join(script_dir, ".." if destination == "parent" else "."))
    zip_path = os.path.join(base_target_dir, name)
    
    log_and_print(f"Archiving to {destination}: {name}", "INFO")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(script_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, script_dir)
                    
                    # 1. Always skip the archive file itself and .git folder
                    if file == name or '.git' in rel_path: continue
                    
                    if type_label == "LOCAL_ZIP":
                        allowed = False
                        # Normalize path to forward slashes for matching
                        match_path = rel_path.replace('\\', '/')
                        
                        for p in RELEASE_WHITELIST:
                            pattern = p.strip()
                            # Folder match (e.g., Plugin/)
                            if pattern.endswith("/") and match_path.startswith(pattern):
                                allowed = True; break
                            # Filename regex match (only if file is in root)
                            if "/" not in match_path:
                                if re.match(pattern, file):
                                    allowed = True; break
                        
                        if not allowed: continue
                    
                    zipf.write(file_path, rel_path)
                    
        file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log_and_print(f"Archive SUCCESS: {zip_path} ({file_size_mb:.2f} MB)", "INFO")
        
        limit = float(cfg.get('MaxZipSizeMB', 100))
        if file_size_mb > limit:
            log_and_print(f"WARNING: Archive size exceeds {limit}MB!", "WARNING")
            
    except Exception as e:
        log_and_print(f"Archive FAILED: {e}", "ERROR")

def generate_changelog(version):
    log_and_print("Generating changelog...", "INFO")
    tag = subprocess.run("git describe --tags --abbrev=0", shell=True, text=True, capture_output=True).stdout.strip()
    cmd = f'git log {tag}..HEAD --pretty=format:"- %s"' if tag else 'git log -n 5 --pretty=format:"- %s"'
    commits = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip() or "- General updates."
    entry = f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n{commits}\n\n"
    content = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f: content = f.read()
    if f"## [{version}]" not in content:
        with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n" + entry + content.replace("# Changelog\n\n", ""))
    return commits

# ==============================================================================
# SYNC LOGIC
# ==============================================================================
def apply_whitelist():
    for item in os.listdir("."):
        if item == ".git": continue
        if item in ["sync.py", "config_sync.ini"]: continue
        allowed = False
        for p in RELEASE_WHITELIST:
            if (p.endswith("/") and item == p[:-1]) or re.match(p, item):
                allowed = True; break
        if not allowed:
            if os.path.isdir(item): shutil.rmtree(item, ignore_errors=True)
            else: os.remove(item)

def handle_master_sync(version, auto, is_deploy):
    mode = "DEPLOY" if is_deploy else "UPDATE"
    if os.path.basename(os.getcwd()) != cfg.get('LocalFolderName'):
        sys.exit(f"[FATAL] Directory mismatch! Expected '{cfg.get('LocalFolderName')}'")
    
    if get_current_branch() == RELEASE_BRANCH:
        check_run(f"git checkout {DEV_BRANCH}")
    
    notes = generate_changelog(version)
    check_run(f"git add {CHANGELOG_PATH}")
    if subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True).stdout.strip():
        check_run(f'git commit -m "v{version} | Auto-changelog update"')

    create_backup(version, f"PRE_{mode}", destination="parent")

    temp_branch = "temp_release_work"
    subprocess.run(f"git branch -D {temp_branch}", shell=True, capture_output=True)
    check_run(f"git checkout -b {temp_branch}")

    apply_whitelist()
    if os.path.exists(README_PATH):
        with open(README_PATH, 'r', encoding='utf-8') as f: txt = f.read()
        new_txt = re.sub(r"(?i)(\*?\*?version\*?\*?[:\s]+)([0-9\.]+)", rf"\g<1>{version}", txt)
        with open(README_PATH, 'w', encoding='utf-8') as f: f.write(new_txt)

    check_run("git add -A")
    check_run(f'git commit -m "Release v{version}" --allow-empty')

    if is_deploy:
        check_run(f"git push {cfg.get('ReleaseRemote')} {temp_branch}:{RELEASE_BRANCH} --force")
    else:
        check_run(f"git checkout {RELEASE_BRANCH}")
        check_run(f"git pull {cfg.get('ReleaseRemote')} {RELEASE_BRANCH}")
        check_run(f'git merge {temp_branch} -X theirs --allow-unrelated-histories -m "Update v{version}"')
        check_run(f"git push {cfg.get('ReleaseRemote')} {RELEASE_BRANCH}")

    subprocess.run(f"git tag -a v{version} -m 'v{version}'", shell=True)
    subprocess.run(f"git push {cfg.get('ReleaseRemote')} v{version}", shell=True)
    
    if is_deploy:
        url = check_run(f"git remote get-url {cfg.get('ReleaseRemote')}")
        repo = re.sub(r'.*github\.com[:/]', '', url).replace('.git', '')
        subprocess.run(f"gh release delete v{version} --repo {repo} -y", shell=True, capture_output=True)
        check_run(f'gh release create v{version} --repo {repo} --title "v{version}" --notes "{notes}"')

    check_run(f"git checkout {DEV_BRANCH} -f")
    subprocess.run(f"git branch -D {temp_branch}", shell=True, capture_output=True)

# ==============================================================================
# MAIN ENTRY
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"MAMBA SYNC TOOL v{SCRIPT_VER}")
    parser.add_argument("--deploy", action="store_true", help="Flattened Master Release")
    parser.add_argument("--update", action="store_true", help="Incremental Master Update")
    parser.add_argument("--full-backup", action="store_true", help="Full ZIP in parent folder")
    parser.add_argument("--zip", action="store_true", help="Local staging ZIP (WhiteListed)")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all prompts")
    parser.add_argument("-o", "--open", action="store_true", help="Open session logs")
    args = parser.parse_args()

    if os.path.basename(os.getcwd()) != cfg.get('LocalFolderName'):
        sys.exit(f"[FATAL] Directory mismatch! Expected '{cfg.get('LocalFolderName')}'")

    VER = get_project_version(args.yes)
    LOG_FILE_PATH = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.log")

    if args.full_backup:
        create_backup(VER, "FULL_BACKUP", destination="parent")
    elif args.zip:
        create_backup(VER, "LOCAL_ZIP", destination="local")
    elif args.deploy:
        handle_master_sync(VER, args.yes, True)
    elif args.update:
        handle_master_sync(VER, args.yes, False)
    else:
        if get_current_branch() == RELEASE_BRANCH:
            check_run(f"git checkout {DEV_BRANCH}")
        check_run("git add .")
        if subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True).stdout.strip():
            msg = "auto sync" if args.yes else input(f"Dev commit msg (v{VER}): ").strip()
            if msg:
                check_run(f'git commit -m "v{VER} | {msg}"')
                check_run(f"git push {cfg.get('DevRemote')} {DEV_BRANCH}")
        else: print("Nothing to sync on dev branch.")

    if args.open:
        log_path = os.path.abspath(LOG_FILE_PATH)
        if os.path.exists(VS_CODE_PATH): subprocess.run([VS_CODE_PATH, log_path], shell=True)
        else: os.startfile(log_path)
