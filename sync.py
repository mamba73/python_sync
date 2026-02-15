import xml.etree.ElementTree as ET
import subprocess
import sys
import argparse
import re
import os
import configparser
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# VERSION & METADATA
# ==============================================================================
SCRIPT_VER = "1.6.0"

# --- PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "config_sync.ini")

# ==============================================================================
# CONFIGURATION & VALIDATION
# ==============================================================================
def load_and_validate_config():
    config = configparser.ConfigParser()
    defaults = {
        'ProjectName': 'CHANGE_ME',
        'DevRemote': 'private',
        'ReleaseRemote': 'origin',
        'DevBranch': 'dev',
        'ReleaseBranch': 'master',
        'ManifestPath': 'manifest.xml',
        'ReadmePath': 'README.md',
        'ChangelogPath': 'CHANGELOG.md',
        'LogDir': 'logs',
        'KeepLogsDays': '7',
        'VSCodePath': r"c:\dev\VSCode\bin\code.cmd",
        'ReleaseWhiteList': 'Plugin/, manifest.xml, .gitignore, LICENSE, CHANGELOG.md, .*\.csproj$, .*\.sln$, .*\.md$',
        'BackupFormat': '{date}_{time}_{type}_{remote}_v{version}_{branch}.zip'
    }
    
    # Initial setup if file is missing
    if not os.path.exists(config_file):
        config['SETTINGS'] = defaults
        with open(config_file, 'w') as f: config.write(f)
        print(f"\n[!] Configuration file created: {config_file}")
        print("[!] Please edit the file and set your 'ProjectName' before running again.\n")
        sys.exit(0)

    config.read(config_file)
    settings = config['SETTINGS']

    # CRITICAL VALIDATION: Check if ProjectName was updated
    if settings.get('ProjectName') == 'CHANGE_ME':
        print(f"\n[FATAL] Configuration is incomplete!")
        print(f"[!] Please update 'ProjectName' in: {os.path.abspath(config_file)}")
        print("[!] Script aborted for safety.\n")
        sys.exit(1)

    return settings

# Global Config Object
cfg = load_and_validate_config()

# Map config to variables
DEV_BRANCH = cfg.get('DevBranch')
RELEASE_BRANCH = cfg.get('ReleaseBranch')
MANIFEST_PATH = cfg.get('ManifestPath')
README_PATH = cfg.get('ReadmePath')
CHANGELOG_PATH = cfg.get('ChangelogPath')
LOG_DIR = os.path.join(script_dir, cfg.get('LogDir'))
VS_CODE_PATH = cfg.get('VSCodePath')
RELEASE_WHITELIST = [item.strip() for item in cfg.get('ReleaseWhiteList').split(',')]
BACKUP_NAME_FORMAT = cfg.get('BackupFormat')

# ==============================================================================
# LOGGING & CLEANUP
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

def purge_old_logs():
    """Removes log files older than KeepLogsDays."""
    try:
        days = int(cfg.get('KeepLogsDays', 7))
        now = datetime.now()
        count = 0
        if os.path.exists(LOG_DIR):
            for file in os.listdir(LOG_DIR):
                fp = os.path.join(LOG_DIR, file)
                if os.path.isfile(fp):
                    if os.path.getmtime(fp) < (now - timedelta(days=days)).timestamp():
                        os.remove(fp)
                        count += 1
        if count > 0: log_and_print(f"Log cleanup: Removed {count} old log files.", "DEBUG")
    except Exception as e: log_and_print(f"Cleanup failed: {e}", "WARNING")

# ==============================================================================
# GIT UTILITIES
# ==============================================================================

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
        log_and_print(f"CRITICAL ERROR: Branch mismatch! Expected {target_branch}, got {current}", "ERROR")
        sys.exit(1)

def verify_directory_safety():
    current_dir = os.path.basename(os.getcwd())
    expected_dir = cfg.get('ProjectName')
    if current_dir != expected_dir:
        log_and_print(f"CRITICAL ERROR: Directory mismatch! Must run in '{expected_dir}'.", "ERROR")
        sys.exit(1)

# ==============================================================================
# CHANGELOG & RELEASE NOTES
# ==============================================================================

def generate_changelog(version):
    log_and_print("Generating changelog from git history...", "INFO")
    last_tag = subprocess.run("git describe --tags --abbrev=0", shell=True, text=True, capture_output=True).stdout.strip()
    
    cmd = f'git log {last_tag}..HEAD --pretty=format:"- %s (%h)"' if last_tag else 'git log -n 5 --pretty=format:"- %s (%h)"'
    commits = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip()
    
    if not commits: commits = "- Performance and stability improvements."

    date_str = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"## [{version}] - {date_str}\n{commits}\n\n"

    old_content = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f: old_content = f.read()

    if f"## [{version}]" not in old_content:
        header = "# Changelog\n\n"
        with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
            f.write(header + new_entry + old_content.replace(header, ""))
        log_and_print(f"CHANGELOG.md updated for v{version}")
    
    return commits

# ==============================================================================
# SYNC PROCESSORS
# ==============================================================================

def apply_whitelist_purge():
    log_and_print("Applying Whitelist Filter for clean release...", "INFO")
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

    if get_current_branch() != DEV_BRANCH:
        check_run(f"git checkout {DEV_BRANCH}")

    release_notes = generate_changelog(version)
    check_run(f"git add {CHANGELOG_PATH}")
    
    if subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True).stdout.strip():
        check_run(f'git commit -m "v{version} | Update changelog for release"')

    # Prep Master
    if is_deploy:
        subprocess.run("git branch -D temp_release", shell=True, capture_output=True)
        check_run(f"git checkout --orphan temp_release {DEV_BRANCH}")
    else:
        check_run(f"git checkout {RELEASE_BRANCH}")
        verify_branch(RELEASE_BRANCH)
        check_run(f"git pull {cfg.get('ReleaseRemote')} {RELEASE_BRANCH}")
        check_run(f"git checkout {DEV_BRANCH} -- .")

    apply_whitelist_purge()
    
    # Version Bump in Readme
    if os.path.exists(README_PATH):
        with open(README_PATH, 'r', encoding='utf-8') as f: content = f.read()
        new_content = re.sub(r"(?i)(\*?\*?version\*?\*?[:\s]+)([0-9\.]+)", rf"\g<1>{version}", content)
        with open(README_PATH, 'w', encoding='utf-8') as f: f.write(new_content)

    check_run("git add -A")
    check_run(f'git commit -m "Release v{version}" --allow-empty')

    if is_deploy:
        check_run(f"git branch -M temp_release {RELEASE_BRANCH}")

    check_run(f"git push {cfg.get('ReleaseRemote')} {RELEASE_BRANCH} {'--force' if is_deploy else ''}")
    subprocess.run(f"git tag -a v{version} -m 'Version {version}'", shell=True)
    subprocess.run(f"git push {cfg.get('ReleaseRemote')} v{version}", shell=True)

    if is_deploy:
        repo_url = check_run(f"git remote get-url {cfg.get('ReleaseRemote')}")
        repo_name = re.sub(r'.*github\.com[:/]', '', repo_url).replace('.git', '')
        log_and_print(f"Creating GH Release v{version}...", "INFO")
        subprocess.run(f"gh release delete v{version} --repo {repo_name} -y", shell=True, capture_output=True)
        check_run(f'gh release create v{version} --repo {repo_name} --title "v{version}" --notes "{release_notes}"')

    check_run(f"git checkout {DEV_BRANCH} -f")
    log_and_print(f"{mode} completed.")

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    verify_directory_safety()
    
    # Dynamic log file name
    ver_tag = "".join(filter(str.isdigit, cfg.get('ProjectName')))[:5]
    LOG_FILE_PATH = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_sync.log")
    
    purge_old_logs()

    parser = argparse.ArgumentParser(description=f"MAMBA SYNC TOOL v{SCRIPT_VER}")
    parser.add_argument("--deploy", action="store_true", help="Flatten master history & GH release.")
    parser.add_argument("--update", action="store_true", help="Incremental release to master.")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all prompts.")
    parser.add_argument("-o", "--open", action="store_true", help="Open current log.")

    args = parser.parse_args()
    log_and_print(f"Mamba Sync Tool v{SCRIPT_VER} initialized.")

    # Get version from manifest
    try:
        tree = ET.parse(MANIFEST_PATH)
        VER = tree.getroot().find('Version').text.strip()
    except: VER = "0.0.0"

    if args.deploy: handle_master_sync(VER, args.yes, is_deploy=True)
    elif args.update: handle_master_sync(VER, args.yes, is_deploy=False)
    else:
        # Standard Dev Sync
        if get_current_branch() != DEV_BRANCH:
            check_run(f"git checkout {DEV_BRANCH} -f")
        check_run("git add .")
        if subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True).stdout.strip():
            msg = "auto sync" if args.yes else input(f"Dev commit msg (v{VER}): ").strip()
            if msg:
                check_run(f'git commit -m "v{VER} | {msg}"')
                check_run(f"git push {cfg.get('DevRemote')} {DEV_BRANCH}")
        else: log_and_print("Nothing to sync on dev.")

    if args.open:
        log_abs = os.path.abspath(LOG_FILE_PATH)
        if os.path.exists(VS_CODE_PATH): subprocess.run([VS_CODE_PATH, log_abs], shell=True)
        else: os.startfile(log_abs)
