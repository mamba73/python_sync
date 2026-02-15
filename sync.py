import xml.etree.ElementTree as ET
import subprocess
import sys
import argparse
import re
import os
import zipfile
import configparser
import shutil
from datetime import datetime

# ==============================================================================
# VERSION & METADATA
# ==============================================================================
# Script for synchronizing private development with public releases.
SCRIPT_VER = "1.4.0"

# ==============================================================================
# RELEASE WHITELIST (Files allowed on Public Master branch)
# ==============================================================================
RELEASE_WHITELIST = [
    "Plugin/", 
    "manifest.xml", 
    ".gitignore", 
    "LICENSE",
    "CHANGELOG.md",
    r".*\.csproj$", 
    r".*\.sln$", 
    r".*\.md$"
]

# ==============================================================================
# BACKUP CONFIGURATION
# ==============================================================================
BACKUP_NAME_FORMAT = "{date}_{time}_{type}_{remote}_mambaTDS_v{version}_{branch}.zip"

# --- CONFIGURATION & PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "config_sync.ini")

def load_config():
    config = configparser.ConfigParser()
    defaults = {
        'LogDir': 'logs',
        'VSCodePath': r"c:\dev\VSCode\bin\code.cmd",
        'ProjectName': 'mamba.TorchDiscordSync',
        'DevRemote': 'private',
        'ReleaseRemote': 'origin',
        'KeepLogsDays': '7'
    }
    updated = False
    if not os.path.exists(config_file):
        config['SETTINGS'] = defaults
        updated = True
    else:
        config.read(config_file)
        if 'SETTINGS' not in config:
            config['SETTINGS'] = {}; updated = True
        for key, value in defaults.items():
            if not config.has_option('SETTINGS', key):
                config.set('SETTINGS', key, value); updated = True
    if updated:
        with open(config_file, 'w') as f: config.write(f)
    return config['SETTINGS']

cfg = load_config()
LOG_DIR = os.path.join(script_dir, cfg.get('LogDir'))
VS_CODE_PATH = cfg.get('VSCodePath')

MANIFEST_PATH = "manifest.xml"
CHANGELOG_PATH = "CHANGELOG.md"
README_PATH = "README.md"
DEV_BRANCH = "dev"
RELEASE_BRANCH = "master"

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def log_and_print(message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{ts}] [{level}] {message}"
    print(formatted_msg)
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except: pass

def check_run(cmd, exit_on_fail=True):
    log_and_print(f"EXECUTING: {cmd}", "DEBUG")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        error_msg = result.stderr.strip()
        log_and_print(f"COMMAND FAILED: {error_msg}", "ERROR")
        if exit_on_fail: sys.exit(1)
        return None
    return result.stdout.strip() if result.stdout else "SUCCESS"

def get_current_branch():
    return subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, text=True, capture_output=True).stdout.strip()

def verify_branch(target_branch):
    current = get_current_branch()
    if current != target_branch:
        log_and_print(f"CRITICAL ERROR: Branch mismatch. Expected {target_branch}, got {current}", "ERROR")
        sys.exit(1)

def verify_directory_safety():
    current_dir = os.path.basename(os.getcwd())
    expected_dir = cfg.get('ProjectName')
    if current_dir != expected_dir:
        log_and_print(f"CRITICAL ERROR: Directory mismatch! Run in '{expected_dir}'.", "ERROR")
        sys.exit(1)

def get_project_version():
    try:
        if not os.path.exists(MANIFEST_PATH): return "0.0.0"
        tree = ET.parse(MANIFEST_PATH)
        root = tree.getroot()
        version_node = root.find('Version')
        return version_node.text.strip() if version_node is not None else "0.0.0"
    except: return "0.0.0"

# ==============================================================================
# CHANGELOG GENERATION SYSTEM
# ==============================================================================
def generate_changelog(version):
    """
    Extracts commit messages since last tag and updates CHANGELOG.md.
    Returns the newly generated notes for GitHub Release.
    """
    log_and_print("Generating changelog from git history...", "INFO")
    
    # 1. Try to find the last tag to get the diff
    last_tag = subprocess.run("git describe --tags --abbrev=0", shell=True, text=True, capture_output=True).stdout.strip()
    
    if last_tag:
        cmd = f'git log {last_tag}..HEAD --pretty=format:"- %s (%h)"'
    else:
        # Fallback if no tags exist: take last 5 commits
        cmd = 'git log -n 5 --pretty=format:"- %s (%h)"'
    
    commits = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip()
    
    if not commits:
        commits = "- Minor internal updates and improvements."

    date_str = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"## [{version}] - {date_str}\n{commits}\n\n"

    # 2. Update local CHANGELOG.md (Prepend)
    old_content = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
            old_content = f.read()

    # Avoid duplicate entry for the same version
    if f"## [{version}]" not in old_content:
        with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n" + new_entry + old_content.replace("# Changelog\n\n", ""))
        log_and_print(f"CHANGELOG.md updated for version {version}")
    
    return commits

# ==============================================================================
# VERSION & README UTILITIES
# ==============================================================================
def update_readme(version):
    try:
        if not os.path.exists(README_PATH): return
        with open(README_PATH, 'r', encoding='utf-8') as f: content = f.read()
        pattern = r"(?i)(\*?\*?version\*?\*?[:\s]+)([0-9\.]+)"
        new_content = re.sub(pattern, rf"\g<1>{version}", content)
        with open(README_PATH, 'w', encoding='utf-8') as f: f.write(new_content)
        log_and_print(f"README version updated to {version}")
    except Exception as e:
        log_and_print(f"README update error: {e}", "WARNING")

# ==============================================================================
# CORE SYNC LOGIC
# ==============================================================================
def apply_whitelist_purge():
    log_and_print("Purging files not in WhiteList...", "INFO")
    for item in os.listdir("."):
        if item == ".git": continue
        is_allowed = False
        for pattern in RELEASE_WHITELIST:
            if pattern.endswith("/") and item == pattern[:-1]: is_allowed = True; break
            if re.match(pattern, item): is_allowed = True; break
        if not is_allowed:
            if os.path.isdir(item): shutil.rmtree(item, ignore_errors=True)
            else: os.remove(item)

def handle_master_sync(version, auto_confirm, is_deploy):
    mode = "DEPLOY (FLATTENED)" if is_deploy else "UPDATE (INCREMENTAL)"
    log_and_print(f"STARTING {mode} v{version}", "WARNING")

    # 1. Dev Pre-check & Changelog
    if get_current_branch() != DEV_BRANCH:
        check_run(f"git checkout {DEV_BRANCH}")

    # Generate notes while still on dev branch
    release_notes = generate_changelog(version)

    check_run("git add CHANGELOG.md")
    status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True).stdout.strip()
    if status:
        check_run(f'git commit -m "v{version} | Update changelog and pre-sync"')

    # 2. Preparation
    if is_deploy:
        subprocess.run("git branch -D temp_release", shell=True, capture_output=True)
        check_run(f"git checkout --orphan temp_release {DEV_BRANCH}")
    else:
        check_run(f"git checkout {RELEASE_BRANCH}")
        verify_branch(RELEASE_BRANCH)
        check_run(f"git pull {cfg.get('ReleaseRemote')} {RELEASE_BRANCH}")
        check_run(f"git checkout {DEV_BRANCH} -- .")

    # 3. Clean & Commit
    apply_whitelist_purge()
    update_readme(version)
    check_run("git add -A")
    commit_msg = f"Release v{version}"
    check_run(f'git commit -m "{commit_msg}" --allow-empty')

    if is_deploy:
        check_run(f"git branch -M temp_release {RELEASE_BRANCH}")

    # 4. Push, Tag & GH Release
    check_run(f"git push {cfg.get('ReleaseRemote')} {RELEASE_BRANCH} {'--force' if is_deploy else ''}")
    
    # Tagging the new release
    subprocess.run(f"git tag -a v{version} -m 'Version {version}'", shell=True)
    subprocess.run(f"git push {cfg.get('ReleaseRemote')} v{version}", shell=True)

    if is_deploy:
        repo_url = check_run(f"git remote get-url {cfg.get('ReleaseRemote')}")
        repo_name = re.sub(r'.*github\.com[:/]', '', repo_url).replace('.git', '')
        log_and_print(f"Creating GitHub Release v{version}...", "INFO")
        subprocess.run(f"gh release delete v{version} --repo {repo_name} -y", shell=True, capture_output=True)
        check_run(f'gh release create v{version} --repo {repo_name} --title "v{version}" --notes "{release_notes}"')

    check_run(f"git checkout {DEV_BRANCH} -f")
    log_and_print(f"{mode} successful.")

def handle_dev(version, auto_yes):
    if get_current_branch() != DEV_BRANCH:
        check_run(f"git checkout {DEV_BRANCH} -f")
    
    update_readme(version)
    check_run("git add .")

    if not subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True).stdout.strip():
        log_and_print("No changes to sync on Dev."); return

    msg = "auto sync" if auto_yes else input(f"Commit msg (v{version}): ").strip()
    if msg:
        check_run(f'git commit -m "v{version} | {msg}"')
        check_run(f"git push {cfg.get('DevRemote')} {DEV_BRANCH}")

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    verify_directory_safety()
    VER = get_project_version()
    LOG_FILE_PATH = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{VER}_sync.log")

    parser = argparse.ArgumentParser(description=f"MAMBA SYNC TOOL v{SCRIPT_VER}")
    parser.add_argument("--deploy", action="store_true", help="Flatten master history & GitHub release.")
    parser.add_argument("--update", action="store_true", help="Incremental master update.")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all prompts.")
    parser.add_argument("-o", "--open", action="store_true", help="Open log.")

    args = parser.parse_args()
    log_and_print(f"Mamba Sync Tool v{SCRIPT_VER} started.")

    if args.deploy: handle_master_sync(VER, args.yes, is_deploy=True)
    elif args.update: handle_master_sync(VER, args.yes, is_deploy=False)
    else: handle_dev(VER, args.yes)
