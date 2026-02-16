import xml.etree.ElementTree as ET
import subprocess
import sys
import argparse
import re
import os
import configparser
import shutil
import zipfile
import time
from datetime import datetime

# ==============================================================================
# VERSION & METADATA
# ==============================================================================
SCRIPT_VER = "1.15.0"

# --- PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "config_sync.ini")

# ==============================================================================
# CONFIGURATION SYSTEM
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
        'BuildStagingDir': 'bin/Release',
        'VSCodePath': r"c:\dev\VSCode\bin\code.cmd",
        'ReleaseWhiteList': r'Plugin/, manifest.xml, .gitignore, LICENSE, CHANGELOG.md, .*\.csproj$, .*\.sln$, .*\.md$',
        'BackupFormat': '{date}_{time}_{type}_{project}_v{version}_{remote}_{branch}.zip'
    }
    if os.path.exists(config_file): config.read(config_file)
    if 'SETTINGS' not in config: config['SETTINGS'] = {}
    updated = False
    for key, value in defaults.items():
        if not config.has_option('SETTINGS', key):
            config.set('SETTINGS', key, value)
            updated = True
    if updated:
        with open(config_file, 'w') as f: config.write(f)
    return config['SETTINGS']

cfg = load_and_sync_config()

# Global Mapping
DEV_BRANCH = cfg.get('DevBranch')
RELEASE_BRANCH = cfg.get('ReleaseBranch')
MANIFEST_PATH = cfg.get('ManifestPath')
README_PATH = cfg.get('ReadmePath')
CHANGELOG_PATH = cfg.get('ChangelogPath')
LOG_DIR = os.path.join(script_dir, cfg.get('LogDir'))
STAGING_DIR = cfg.get('BuildStagingDir')
RELEASE_WHITELIST = [item.strip() for item in cfg.get('ReleaseWhiteList').split(',')]
BACKUP_NAME_FORMAT = cfg.get('BackupFormat')
PROJECT_NAME = cfg.get('RemoteProjectName')
VS_CODE_PATH = cfg.get('VSCodePath')

# ==============================================================================
# UTILITIES
# ==============================================================================
def log_and_print(message, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] [{level}] {message}"
    print(formatted)
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    try:
        log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.log")
        with open(log_file, "a", encoding="utf-8") as f: f.write(formatted + "\n")
    except: pass

def check_run(cmd, exit_on_fail=True):
    log_and_print(f"DEBUG: Executing command -> {cmd}", "DEBUG")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        log_and_print(f"FAILED: {res.stderr.strip()}", "ERROR")
        if exit_on_fail: sys.exit(1)
        return None
    return res.stdout.strip() if res.stdout else "SUCCESS"

def get_current_branch():
    branch = subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, text=True, capture_output=True).stdout.strip()
    log_and_print(f"DEBUG: Current branch detected as -> {branch}", "DEBUG")
    return branch

def get_project_version(auto_yes=False):
    current_ver = None
    if os.path.exists(MANIFEST_PATH):
        try:
            tree = ET.parse(MANIFEST_PATH)
            node = tree.getroot().find('Version')
            if node is not None: current_ver = node.text.strip()
        except: pass
    if not current_ver: current_ver = cfg.get('DefaultVersion', '1.0.0')
    print(f"\n[SYSTEM] Current Manifest Version: {current_ver}")
    if not auto_yes:
        user_input = input(f"Confirm version for this session [{current_ver}]: ").strip()
        if user_input: current_ver = user_input
    return current_ver

def update_readme_version(version):
    if not os.path.exists(README_PATH):
        log_and_print(f"WARNING: {README_PATH} not found. Skipping update.", "WARNING")
        return False
    
    log_and_print(f"DEBUG: Updating README version to {version}...", "DEBUG")
    with open(README_PATH, 'r', encoding='utf-8') as f: txt = f.read()
    pattern = r"(?i)(\*?\*?Version\*?\*?[:\s]+)([0-9\.]+)"
    
    # Debug search
    old_ver = re.search(pattern, txt)
    if old_ver:
        log_and_print(f"DEBUG: Found old version string in README: {old_ver.group(0)}", "DEBUG")
    
    new_txt, count = re.subn(pattern, rf"\g<1>{version}", txt)
    if count > 0:
        with open(README_PATH, 'w', encoding='utf-8') as f: f.write(new_txt)
        log_and_print(f"SUCCESS: README.md updated to v{version} (Matches: {count})", "INFO")
        return True
    else:
        log_and_print("ERROR: Version pattern NOT FOUND in README.md!", "ERROR")
        return False

def generate_changelog(version):
    tag_res = subprocess.run("git describe --tags --abbrev=0", shell=True, text=True, capture_output=True)
    tag = tag_res.stdout.strip() if tag_res.returncode == 0 else None
    cmd = f'git log {tag}..HEAD --pretty=format:"- %s"' if tag else 'git log -n 5 --pretty=format:"- %s"'
    commits = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip() or "- General updates."
    entry = f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n{commits}\n\n"
    content = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f: content = f.read()
    if f"## [{version}]" not in content:
        header = "# Changelog\n\n"
        with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
            f.write(header + entry + content.replace(header, ""))
    return commits

def create_zip(source_dir, output_file, is_whitelist=False):
    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source_dir)
                    if ".git" in rel_path or file == os.path.basename(output_file): continue
                    if is_whitelist:
                        match_path = rel_path.replace('\\', '/')
                        allowed = any((p.endswith("/") and match_path.startswith(p)) or re.match(p, file) for p in RELEASE_WHITELIST)
                        if not allowed: continue
                    zipf.write(file_path, rel_path)
        return True
    except Exception as e:
        log_and_print(f"ZIP Failed: {e}", "ERROR")
        return False

# ==============================================================================
# DEPLOY & UPDATE LOGIC
# ==============================================================================
def apply_whitelist():
    protected = ["sync.py", "config_sync.ini", ".git"]
    for item in os.listdir("."):
        if item in protected: continue
        allowed = any((p.endswith("/") and item == p[:-1]) or re.match(p, item) for p in RELEASE_WHITELIST)
        if not allowed:
            if os.path.isdir(item): shutil.rmtree(item, ignore_errors=True)
            else: os.remove(item)

def handle_master_release(version, is_deploy):
    mode = "DEPLOY" if is_deploy else "UPDATE"
    print(f"\n--- STARTING {mode} v{version} ---")
    
    # 1. Update Metadata
    update_readme_version(version)
    notes = generate_changelog(version)
    
    bin_zip = f"{PROJECT_NAME}_v{version}_bin.zip"
    bin_zip_full = os.path.abspath(bin_zip)
    
    if os.path.exists(STAGING_DIR):
        log_and_print(f"Zipping build assets from {STAGING_DIR}...", "INFO")
        create_zip(STAGING_DIR, bin_zip_full)

    dep_folder, backup_path = "Dependencies", os.path.abspath(os.path.join(script_dir, "..", "_sync_temp_deps"))
    deps_exist = os.path.exists(dep_folder)
    if deps_exist:
        if os.path.exists(backup_path): shutil.rmtree(backup_path)
        shutil.move(dep_folder, backup_path)

    try:
        temp = "temp_release_work"
        subprocess.run(f"git branch -D {temp}", shell=True, capture_output=True)
        if is_deploy:
            check_run(f"git checkout --orphan {temp}")
        else:
            check_run(f"git checkout {RELEASE_BRANCH}")
            check_run(f"git pull {cfg.get('ReleaseRemote')} {RELEASE_BRANCH}")
            check_run(f"git checkout -b {temp}")
            
        apply_whitelist()
        check_run("git add -A")
        check_run(f'git commit -m "Release v{version}" --allow-empty')
        check_run(f"git push {cfg.get('ReleaseRemote')} {temp}:{RELEASE_BRANCH} --force")
        check_run(f"git tag -f v{version}")
        check_run(f"git push {cfg.get('ReleaseRemote')} v{version} --force")

        if is_deploy:
            url = check_run(f"git remote get-url {cfg.get('ReleaseRemote')}")
            repo = re.sub(r'.*github\.com[:/]', '', url).replace('.git', '')
            subprocess.run(f"gh release delete v{version} --repo {repo} -y", shell=True, capture_output=True)
            check_run(f'gh release create v{version} --repo {repo} --title "v{version}" --notes "{notes}"')
            if os.path.exists(bin_zip_full):
                time.sleep(2)
                check_run(f'gh release upload v{version} "{bin_zip_full}" --repo {repo} --clobber')

    finally:
        check_run(f"git checkout {DEV_BRANCH} -f")
        if deps_exist: shutil.move(backup_path, dep_folder)
        if os.path.exists(bin_zip_full): os.remove(bin_zip_full)
        subprocess.run(f"git branch -D {temp}", shell=True, capture_output=True)

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    print(f"\n====================================================")
    print(f"  MAMBA SYNC TOOL v{SCRIPT_VER} | {PROJECT_NAME}")
    print(f"====================================================\n")

    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true", help="Flattened Release")
    parser.add_argument("--update", action="store_true", help="Incremental Update")
    parser.add_argument("--full-backup", action="store_true", help="Source Backup")
    parser.add_argument("--zip", action="store_true", help="Whitelist ZIP")
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("-o", "--open", action="store_true")
    args = parser.parse_args()

    VER = get_project_version(args.yes)
    LOG_FILE_PATH = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.log")

    if args.full_backup:
        name = BACKUP_NAME_FORMAT.format(date=datetime.now().strftime("%Y%m%d"), time="", type="FULL", project=PROJECT_NAME, version=VER, remote="LOC", branch="DEV")
        create_zip(script_dir, os.path.join("..", name))
    elif args.zip:
        create_zip(script_dir, f"{PROJECT_NAME}_v{VER}_source.zip", is_whitelist=True)
    elif args.deploy: handle_master_release(VER, True)
    elif args.update: handle_master_release(VER, False)
    else:
        # --- SAFE STANDARD SYNC ---
        curr = get_current_branch()
        if curr != DEV_BRANCH:
            log_and_print(f"Switching from {curr} to {DEV_BRANCH}...", "INFO")
            check_run(f"git checkout {DEV_BRANCH} -f")
        
        # Update README AFTER ensuring we are on the right branch
        update_readme_version(VER)
        
        check_run("git add .")
        
        # Check if there's actually something to commit
        status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True).stdout.strip()
        if status:
            log_and_print(f"Changes detected:\n{status}", "DEBUG")
            msg = "auto sync" if args.yes else input(f"Commit msg (v{VER}): ").strip()
            if msg and check_run(f'git commit -m "v{VER} | {msg}"'):
                check_run(f"git push {cfg.get('DevRemote')} {DEV_BRANCH}")
        else:
            log_and_print("Nothing to sync, everything up to date.", "INFO")

    if args.open:
        log_path = os.path.abspath(LOG_FILE_PATH)
        if os.path.exists(VS_CODE_PATH): subprocess.run([VS_CODE_PATH, log_path], shell=True)
        else: os.startfile(log_path)
