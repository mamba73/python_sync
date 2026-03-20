# ==============================================================================
# MAMBA SYNC TOOL
# Version: 1.22.1
#
# PURPOSE:
# Maintains two separate Git branches with different purposes and histories:
#
# DEV BRANCH (private):
#   - Full development history (100+ commits, tools, docs, experiments)
#   - Contains everything: build scripts, test files, documentation
#   - Pushed to private remote (private/dev or origin/dev)
#
# MASTER BRANCH (public on GitHub):
#   - Clean, minimal history (only sync tool commits)
#   - Contains ONLY whitelisted files (Plugin/, manifest.xml, README, etc.)
#   - Each update adds +1 commit (linear history, NO dev commits leak)
#   - Example: commit 1: initial → commit 2: fix → commit 3: feat
#
# COMMANDS:
# python sync.py             → Commit & push dev changes (private)
# python sync.py --update    → Update public master (+1 commit, whitelisted files)
# python sync.py --release   → --update + create ZIPs + GitHub Release
# python sync.py --deploy    → WIPE master history (orphan commit, use for cleanup)
# python sync.py --reset     → Force pull master from GitHub (safety mechanism)
#
# GUARANTEES:
# - Dev branch preserved (safety branch before operations)
# - Master has ZERO dev history (clean slate, whitelisted files only)
# - Developers can git pull master without conflicts
#
# VERSION HISTORY:
# 1.22.1 - Fixed branch detection (uses actual current branch, not default)
#        - Fixed log filename format: YYYY-MM-DD_HHMMSS_sync--command.log
#        - Auto-detect project folder name for LocalFolderName at init
#        - Create LogDir if it doesn't exist (including parent dirs)
# 1.22.0 - CRITICAL FIX: --deploy now creates true orphan commit (ZERO parents)
#        - Fixed: git index cleared before orphan commit
#        - Fixed: LogDir dynamically protected (not hardcoded)
#        - Version bumped in header for clarity
# ==============================================================================

import os
import sys
import re
import argparse
import subprocess
import configparser
import zipfile
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET

# ==============================================================================
# VERSION
# ==============================================================================
SCRIPT_VER = "1.22.1"

# ==============================================================================
# PATHS
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config_sync.ini")

# ==============================================================================
# PROTECTED FILES (never wiped during master clean)
# Note: LogDir is protected dynamically in wipe functions
# ==============================================================================
PROTECTED_ITEMS_BASE = {".git", "config_sync.ini", "sync.py"}

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DEFAULT_CONFIG = {
    "SETTINGS": {
        "LocalFolderName":           os.path.basename(SCRIPT_DIR),
        "RemoteProjectName":         os.path.basename(SCRIPT_DIR),
        "DefaultVersion":            "0.1.0",
        "DevRemote":                 "origin",
        "ReleaseRemote":             "origin",
        "DevBranch":                 "dev",
        "ReleaseBranch":             "master",
        "ManifestPath":              "manifest.xml",
        "ReadmePath":                "README.md",
        "ReadmeVersionPattern":      r"(Version[:\s]+)([0-9\.]+)",
        "ChangelogPath":             "CHANGELOG.md",
        "LogDir":                    "logs",
        "VSCodePath":                r"c:\dev\VSCode\bin\code.cmd",
        "ReleaseWhiteList":          "Plugin/, .gitignore, CHANGELOG.md, LICENSE, manifest.xml, README.md",
        "BackupFormat":              "{date}_{time}_{type}_{project}_v{version}_{remote}_{branch}.zip",
        "BuildStagingDir":           "bin/Release",
        "BinaryStagingDir":          "build_staging",
        "EnableLoggingForZip":       "true",
        "EnableLoggingForFullBackup":"true",
    }
}

CONFIG_COMMENTS = """\
# ==============================================================================
# MAMBA SYNC TOOL CONFIGURATION
#
# DefaultVersion:
#   Project version fallback if manifest.xml is missing.
#
# ReadmeVersionPattern:
#   Regex used to locate version string in README.md.
#
# ReleaseWhiteList:
#   Files and folders included in LOCAL_ZIP and public releases.
#   Rules:
#     - "SomeFolder/"    -> includes the folder and ALL its contents recursively
#     - "README.md"      -> includes only that exact file (root level)
#   NO wildcards. NO regex. What you list is what goes in.
#
# BinaryStagingDir:
#   Directory containing compiled binaries for --release.
#
# BackupFormat placeholders:
#   {date}     YYYY-MM-DD
#   {time}     HHMMSS
#   {type}     LOCAL_ZIP | FULL_BACKUP | SOURCE | BIN
#   {project}
#   {version}
#   {remote}
#   {branch}
# ==============================================================================

"""

# ==============================================================================
# LOGGING
# ==============================================================================
CURRENT_LOG_FILE = None

def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    if CURRENT_LOG_FILE:
        try:
            with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def write_log_header(command, log_file_path):
    """Write header to log file with command, version, and path."""
    header = f"""\
================================================================================
MAMBA SYNC TOOL v{SCRIPT_VER}
Command: {command}
Log file: {log_file_path}
Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

"""
    try:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(header)
    except Exception:
        pass


# ==============================================================================
# CONFIG LOADER
# ==============================================================================
def load_and_sync_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = configparser.ConfigParser()
        cfg.read_dict(DEFAULT_CONFIG)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(CONFIG_COMMENTS)
            cfg.write(f)
        print("Default config created. Please review config_sync.ini.")
        sys.exit(0)

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")

    if "SETTINGS" not in cfg:
        cfg["SETTINGS"] = {}

    updated = False
    for k, v in DEFAULT_CONFIG["SETTINGS"].items():
        if k not in cfg["SETTINGS"]:
            cfg["SETTINGS"][k] = v
            updated = True

    if updated:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(CONFIG_COMMENTS)
            cfg.write(f)
        log("Config updated with new default keys.", "DEBUG")

    return cfg["SETTINGS"]


def cfgget(cfg, key, default=""):
    """Case-insensitive config get with fallback."""
    v = cfg.get(key.lower()) or cfg.get(key)
    return v if v else default


def get_protected_items(cfg):
    """Get protected items including dynamic LogDir."""
    log_dir = cfgget(cfg, "LogDir", "logs")
    # Split path to get top-level directory (e.g., "doc/logs" -> "doc")
    log_dir_root = log_dir.split('/')[0].split('\\')[0]
    protected = PROTECTED_ITEMS_BASE.copy()
    protected.add(log_dir_root)  # Protect entire log directory tree
    return protected


# ==============================================================================
# VERSION RESOLUTION
# ==============================================================================
def resolve_version(cfg):
    manifest = cfgget(cfg, "ManifestPath", "manifest.xml")
    if os.path.exists(manifest):
        try:
            tree = ET.parse(manifest)
            node = tree.getroot().find("Version")
            if node is not None and node.text:
                log(f"Version resolved from manifest.xml: {node.text.strip()}", "DEBUG")
                return node.text.strip()
        except Exception as e:
            log(f"Manifest read failed: {e}", "ERROR")
    ver = cfgget(cfg, "DefaultVersion", "0.1.0")
    log(f"Version resolved from DefaultVersion: {ver}", "DEBUG")
    return ver


# ==============================================================================
# README UPDATE
# ==============================================================================
def update_readme(cfg, version):
    path    = cfgget(cfg, "ReadmePath", "README.md")
    pattern = cfgget(cfg, "ReadmeVersionPattern", r"(Version[:\s]+)([0-9\.]+)")
    if not os.path.exists(path):
        log("README not found, skipping update.", "DEBUG")
        return
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    new_txt, count = re.subn(pattern, rf"\g<1>{version}", txt)
    if count == 0:
        log("README version pattern not found, applying generic fallback.", "DEBUG")
        new_txt = re.sub(r"\d+\.\d+\.\d+", version, txt, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_txt)
    log(f"README updated to version {version}.", "DEBUG")


# ==============================================================================
# WHITELIST MATCHING
# ==============================================================================
def parse_whitelist(cfg):
    raw = cfgget(cfg, "ReleaseWhiteList", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def whitelist_matches(rel_path, whitelist):
    for entry in whitelist:
        if entry.endswith("/"):
            if rel_path.startswith(entry):
                return True
        else:
            if rel_path == entry:
                return True
    return False


# ==============================================================================
# ZIP CREATION
# ==============================================================================
def create_zip(source_dir, output_path, whitelist=None, include_git=False):
    output_path_abs = os.path.abspath(output_path)
    source_dir_abs  = os.path.abspath(source_dir)
    log(f"Creating ZIP  : {output_path_abs}", "DEBUG")
    log(f"  Source      : {source_dir_abs}", "DEBUG")
    log(f"  Whitelist   : {whitelist if whitelist is not None else 'ALL (no filter)'}", "DEBUG")
    log(f"  Include .git: {include_git}", "DEBUG")

    with zipfile.ZipFile(output_path_abs, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(source_dir_abs):
            if not include_git:
                dirs[:] = [d for d in dirs if d != ".git"]

            for filename in files:
                full = os.path.join(root, filename)
                if os.path.abspath(full) == output_path_abs:
                    continue
                rel = os.path.relpath(full, source_dir_abs).replace("\\", "/")
                if whitelist is not None:
                    if not whitelist_matches(rel, whitelist):
                        continue
                z.write(full, rel)
                log(f"  + {rel}", "DEBUG")

    size_mb = os.path.getsize(output_path_abs) / (1024 * 1024)
    log(f"ZIP created: {output_path_abs} ({size_mb:.2f} MB)", "INFO")


# ==============================================================================
# BACKUP NAMING
# ==============================================================================
def backup_name(cfg, btype, version, remote=None, branch=None):
    fmt = cfgget(cfg, "BackupFormat",
                 "{date}_{time}_{type}_{project}_v{version}_{remote}_{branch}.zip")
    
    # If branch not provided, use ACTUAL current branch
    if branch is None:
        branch = current_branch()
    
    return fmt.format(
        date    = datetime.now().strftime("%Y-%m-%d"),
        time    = datetime.now().strftime("%H%M%S"),
        type    = btype,
        project = cfgget(cfg, "RemoteProjectName", "PROJECT"),
        version = version,
        remote  = remote or "LOCAL",
        branch  = branch,
    )


# ==============================================================================
# GIT HELPERS
# ==============================================================================
def run(cmd, abort_on_error=True):
    log(f"EXEC: {cmd}", "DEBUG")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=SCRIPT_DIR)
    if res.stdout.strip():
        log(res.stdout.strip(), "DEBUG")
    if res.stderr.strip():
        log(res.stderr.strip(), "DEBUG")
    if res.returncode != 0:
        log(f"Command failed (rc={res.returncode}).", "ERROR")
        if abort_on_error:
            sys.exit(1)
    return res.stdout.strip()


def run_ok(cmd):
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=SCRIPT_DIR)
    return res.returncode == 0, res.stdout.strip()


def is_dirty():
    _, out = run_ok("git status --porcelain")
    return bool(out.strip())


def current_branch():
    return run("git rev-parse --abbrev-ref HEAD")


def branch_exists_local(branch):
    ok, _ = run_ok(f"git rev-parse --verify {branch}")
    return ok


def branch_exists_remote(remote, branch):
    ok, _ = run_ok(f"git ls-remote --exit-code {remote} refs/heads/{branch}")
    return ok


def get_current_commit():
    """Get current HEAD commit hash."""
    ok, commit = run_ok("git rev-parse HEAD")
    return commit if ok else None


# ==============================================================================
# DEV SAFETY GUARD
# ==============================================================================
class DevSafetyGuard:
    """
    Creates a safety branch before operations, restores dev state on exit.
    """
    
    def __init__(self, operation):
        self.operation       = operation
        self.original_branch = None
        self.was_dirty       = False
        self.safety_branch   = None
        self.initial_commit  = None
        
    def __enter__(self):
        self.original_branch = current_branch()
        self.was_dirty       = is_dirty()
        self.initial_commit  = get_current_commit()
        self.safety_branch   = f"sync-safety-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        log(f"Creating safety branch: {self.safety_branch}", "INFO")
        
        if self.was_dirty:
            log("Staging all changes for safety snapshot...", "DEBUG")
            run("git add -A")
            run('git commit --no-verify -m "SYNC SAFETY SNAPSHOT"')
            run(f"git branch {self.safety_branch}")
            run("git reset --soft HEAD~1")
            run("git reset")
            log("Dev restored to original dirty state.", "DEBUG")
        else:
            run(f"git branch {self.safety_branch}")
            log("Safety branch created (clean state).", "DEBUG")
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        current = current_branch()
        if current != self.original_branch:
            log(f"Returning to {self.original_branch}...", "DEBUG")
            run(f"git checkout {self.original_branch}", abort_on_error=False)
            
        now_dirty = is_dirty()
        current_commit = get_current_commit()
        commits_made = current_commit != self.initial_commit
        
        if self.was_dirty and not now_dirty and not commits_made:
            log("", "ERROR")
            log("=" * 70, "ERROR")
            log("  CRITICAL: Dev working tree state was lost!", "ERROR")
            log("  Restoring from safety branch...", "ERROR")
            log("=" * 70, "ERROR")
            run(f"git reset --hard {self.safety_branch}")
            run("git reset HEAD~1")
            log("Dev state restored from safety branch.", "INFO")
        elif commits_made:
            log(f"Dev state: commits made during operation (expected).", "DEBUG")
        elif self.was_dirty and now_dirty:
            log(f"Dev state: dirty (preserved).", "DEBUG")
        else:
            log(f"Dev state: clean (preserved).", "DEBUG")
        
        log("", "INFO")
        log(f"Safety branch: {self.safety_branch}", "INFO")
        log("Contains complete snapshot of dev before sync operation.", "INFO")
        log(f"To delete: git branch -D {self.safety_branch}", "INFO")
        log("", "INFO")
        
        return False


# ==============================================================================
# GITHUB CLI CHECK
# ==============================================================================
def require_gh():
    ok, _ = run_ok("gh --version")
    if not ok:
        log("", "ERROR")
        log("===================================================================", "ERROR")
        log("  GitHub CLI (gh) is NOT installed or not found in PATH.", "ERROR")
        log("", "ERROR")
        log("  GitHub CLI is required for --release and --deploy.", "ERROR")
        log("  Download: https://cli.github.com/", "ERROR")
        log("  After install: gh auth login", "ERROR")
        log("===================================================================", "ERROR")
        sys.exit(1)
    log("GitHub CLI (gh) found.", "DEBUG")


# ==============================================================================
# CHANGELOG
# ==============================================================================
def get_log_since_last_tag():
    ok, last_tag = run_ok("git describe --tags --abbrev=0")
    if ok and last_tag:
        ok2, out = run_ok(f"git log {last_tag}..HEAD --oneline --no-merges")
    else:
        ok2, out = run_ok("git log --oneline --no-merges -30")
    if ok2 and out:
        return out.splitlines()
    return []


def update_changelog(cfg, version):
    path  = cfgget(cfg, "ChangelogPath", "CHANGELOG.md")
    lines = get_log_since_last_tag()
    if not lines:
        log("No new commits found for changelog.", "DEBUG")
        return

    entry  = f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    entry += "\n".join(f"- {l}" for l in lines)
    entry += "\n\n"

    existing = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if f"## [{version}]" in existing:
            log(f"Changelog already contains [{version}], skipping.", "DEBUG")
            return

    with open(path, "w", encoding="utf-8") as f:
        f.write(entry + existing)
    log(f"Changelog updated: {path}", "INFO")


# ==============================================================================
# COMMIT MESSAGE INPUT
# ==============================================================================
COMMIT_CONVENTIONS = """\
  Commit conventions:
    feat:   New feature
    fix:    Bug fix
    refac:  Code cleanup / refactor
    perf:   Performance improvement
    docs:   Documentation changes
    chore:  Tooling / CI / build tasks

  Example: feat: Add auto-changelog generation
"""

def ask_commit_msg(default_msg):
    print(COMMIT_CONVENTIONS)
    msg = input(f"  Commit message [{default_msg}]: ").strip()
    if not msg:
        msg = default_msg
    return msg


# ==============================================================================
# CLEAN SLATE COPY
# ==============================================================================
def copy_whitelisted_files(dev_branch, whitelist):
    """
    Copy ONLY whitelisted files from dev_branch to current working tree.
    Uses git restore --source=dev (atomic, handles binary files).
    """
    log(f"Copying whitelisted files from {dev_branch}...", "INFO")

    ok, ls_output = run_ok(f"git ls-tree -r --name-only {dev_branch}")
    if not ok or not ls_output:
        log("No files found in dev branch.", "ERROR")
        return False

    dev_files = [f.strip() for f in ls_output.splitlines() if f.strip()]
    log(f"Dev branch contains {len(dev_files)} files.", "DEBUG")

    copied_count = 0
    for rel_path in dev_files:
        rel_path_normalized = rel_path.replace("\\", "/")
        
        if not whitelist_matches(rel_path_normalized, whitelist):
            log(f"  SKIP: {rel_path_normalized}", "DEBUG")
            continue

        ok, _ = run_ok(f'git restore --source={dev_branch} --worktree -- "{rel_path}"')
        if ok:
            log(f"  + {rel_path_normalized}", "DEBUG")
            copied_count += 1
        else:
            log(f"  FAIL: {rel_path_normalized}", "DEBUG")

    log(f"Copied {copied_count} whitelisted files.", "INFO")
    return copied_count > 0


# ==============================================================================
# OPERATIONS
# ==============================================================================

def cmd_dev_sync(cfg, version, args):
    log("Starting DEV sync...", "INFO")
    update_readme(cfg, version)

    _, status = run_ok("git status --porcelain")
    log(f"Git status: {status if status else '[CLEAN]'}", "DEBUG")

    if not status:
        log("Nothing to commit. DEV sync aborted.", "INFO")
        return

    run("git add .")

    default_msg = f"[{version}] | auto commit dev sync"
    commit_msg  = default_msg if args.yes else ask_commit_msg(default_msg)

    run(f'git commit -m "{commit_msg}"')
    run(f"git push {cfgget(cfg, 'DevRemote', 'origin')} {cfgget(cfg, 'DevBranch', 'dev')}")
    log("DEV sync finished.", "INFO")


def cmd_zip(cfg, version):
    whitelist = parse_whitelist(cfg)
    log(f"Whitelist entries ({len(whitelist)}): {whitelist}", "DEBUG")

    name = backup_name(cfg, "LOCAL_ZIP", version, remote="LOCAL")
    out  = os.path.join(SCRIPT_DIR, name)

    create_zip(SCRIPT_DIR, out, whitelist=whitelist, include_git=False)
    log("ZIP finished.", "INFO")


def cmd_full_backup(cfg, version):
    name       = backup_name(cfg, "FULL_BACKUP", version, remote="LOCAL")
    parent_dir = os.path.dirname(SCRIPT_DIR)
    out        = os.path.join(parent_dir, name)

    log(f"Full backup -> {out}", "INFO")
    log("No filter. .git INCLUDED. Complete snapshot.", "INFO")

    create_zip(SCRIPT_DIR, out, whitelist=None, include_git=True)
    log("Full backup finished.", "INFO")


def cmd_update(cfg, version, args):
    """
    Clean slate master update with ZERO dev history leak.
    
    Flow:
    1. Checkout master
    2. Fetch + reset --hard to remote master (clean slate)
    3. Wipe + copy whitelisted files from dev
    4. Commit (+1 commit on master)
    5. Push (fast-forward)
    
    Guarantees ZERO dev history on public master.
    """
    dev_branch     = cfgget(cfg, "DevBranch",     "dev")
    release_branch = cfgget(cfg, "ReleaseBranch", "master")
    dev_remote     = cfgget(cfg, "DevRemote",     "origin")
    release_remote = cfgget(cfg, "ReleaseRemote", "origin")
    whitelist      = parse_whitelist(cfg)
    protected_items = get_protected_items(cfg)

    with DevSafetyGuard("update"):
        # Update metadata on dev
        update_readme(cfg, version)
        update_changelog(cfg, version)

        _, s = run_ok("git status --porcelain")
        if s:
            run("git add .")
            run(f'git commit -m "[{version}] | readme + changelog update"')

        # Get commit message
        default_msg = f"[{version}] | public update"
        commit_msg  = default_msg if args.yes else ask_commit_msg(default_msg)

        # Checkout master
        log(f"Switching to {release_branch}...", "INFO")
        if branch_exists_local(release_branch):
            run(f"git checkout {release_branch}")
        elif branch_exists_remote(release_remote, release_branch):
            run(f"git checkout -b {release_branch} {release_remote}/{release_branch}")
        else:
            log(f"Release branch '{release_branch}' not found.", "ERROR")
            log(f"Create it: git checkout -b {release_branch} && git push -u {release_remote} {release_branch}", "ERROR")
            sys.exit(1)

        # Sync with remote master (fetch + reset, NO pull/merge!)
        if branch_exists_remote(release_remote, release_branch):
            log("=" * 70, "INFO")
            log("CRITICAL STEP: Syncing local master with remote", "INFO")
            log("Method: fetch + reset --hard (NO pull/merge!)", "INFO")
            log("This guarantees ZERO dev history leak.", "INFO")
            log("=" * 70, "INFO")
            
            run(f"git fetch {release_remote} {release_branch}")
            run(f"git reset --hard {release_remote}/{release_branch}")
            
            log("Local master is now IDENTICAL to remote master.", "INFO")

        # WIPE CLEAN (except protected items)
        log("Wiping master working tree (except protected items)...", "INFO")
        log(f"Protected items: {protected_items}", "DEBUG")
        for item in os.listdir(SCRIPT_DIR):
            if item in protected_items:
                log(f"  PROTECTED: {item}", "DEBUG")
                continue
            path = os.path.join(SCRIPT_DIR, item)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                log(f"  REMOVED: {item}", "DEBUG")
            except Exception as e:
                log(f"Failed to remove {item}: {e}", "DEBUG")
        log("Working tree wiped.", "DEBUG")

        # COPY whitelisted files
        success = copy_whitelisted_files(dev_branch, whitelist)
        if not success:
            log("CRITICAL: File copy failed.", "ERROR")
            sys.exit(1)

        # Commit
        run("git add .")
        run(f'git commit --allow-empty -m "{commit_msg}"')

        # Push
        log(f"Pushing to {release_remote}/{release_branch}...", "INFO")
        run(f"git push {release_remote} {release_branch}")

        log("=" * 70, "INFO")
        log("Public master updated successfully.", "INFO")
        log("Master history: clean, linear, ZERO dev commits.", "INFO")
        log("=" * 70, "INFO")

    log("UPDATE finished.", "INFO")


def cmd_release(cfg, version, args):
    require_gh()

    release_remote = cfgget(cfg, "ReleaseRemote", "origin")
    release_branch = cfgget(cfg, "ReleaseBranch", "master")
    whitelist      = parse_whitelist(cfg)
    bin_dir        = cfgget(cfg, "BinaryStagingDir", "build_staging")

    cmd_update(cfg, version, args)

    # Source ZIP
    src_name = backup_name(cfg, "SOURCE", version,
                           remote=release_remote, branch=release_branch)
    src_path = os.path.join(SCRIPT_DIR, src_name)
    log("Creating SOURCE ZIP...", "INFO")
    create_zip(SCRIPT_DIR, src_path, whitelist=whitelist, include_git=False)

    # Binary ZIP
    bin_path_abs = os.path.join(SCRIPT_DIR, bin_dir)
    bin_zip = None
    if os.path.isdir(bin_path_abs):
        bin_name = backup_name(cfg, "BIN", version,
                               remote=release_remote, branch=release_branch)
        bin_zip  = os.path.join(SCRIPT_DIR, bin_name)
        log(f"Creating BIN ZIP from {bin_dir}...", "INFO")
        create_zip(bin_path_abs, bin_zip, whitelist=None, include_git=False)
    else:
        log(f"Binary dir '{bin_dir}' not found - skipping BIN ZIP.", "INFO")

    # GitHub Release
    tag = f"v{version}"
    log(f"Creating GitHub Release: {tag}", "INFO")

    upload_files = f'"{src_path}"'
    if bin_zip:
        upload_files += f' "{bin_zip}"'

    run(f'gh release create {tag} {upload_files} '
        f'--title "Release {tag}" '
        f'--notes "Release {tag}"')

    log("RELEASE finished.", "INFO")


def cmd_deploy(cfg, version, args):
    """
    WIPE master history completely. Creates orphan commit with WHITELISTED files only.
    
    CRITICAL FIX in v1.22.0:
    - Clears git index after checkout --orphan
    - Ensures ZERO parent commits (true orphan)
    - Previous commits become unreachable
    
    Use this for:
    - Initial release (first time setup)
    - Cleanup when master has unwanted history
    
    Flow:
    1. Checkout orphan temp branch
    2. CLEAR git index (git rm -rf .)
    3. Copy ONLY whitelisted files from dev
    4. Create orphan commit (ZERO parents)
    5. Force update master ref to this commit
    6. Force push
    
    This ensures master has EXACTLY 1 commit with ONLY whitelisted files.
    Previous commits become unreachable and will be garbage collected.
    
    WARNING: Force pushes to remote. Developers will need to:
      git fetch origin
      git reset --hard origin/master
    """
    require_gh()

    dev_branch     = cfgget(cfg, "DevBranch",     "dev")
    release_branch = cfgget(cfg, "ReleaseBranch", "master")
    release_remote = cfgget(cfg, "ReleaseRemote", "origin")
    whitelist      = parse_whitelist(cfg)
    protected_items = get_protected_items(cfg)

    if not args.yes:
        print()
        print("  WARNING: --deploy will DESTROY public master history.")
        print(f"     Remote: {release_remote}")
        print(f"     Branch: {release_branch}")
        print()
        print("  This creates a NEW orphan commit with ZERO history.")
        print("  Previous commits become unreachable.")
        print()
        print("  Developers will need to sync with:")
        print(f"     git fetch {release_remote}")
        print(f"     git reset --hard {release_remote}/{release_branch}")
        print()
        print("  For normal updates, use --update instead.")
        print()
        ans = input("     Type YES to confirm: ").strip()
        if ans != "YES":
            log("Deploy aborted.", "INFO")
            sys.exit(0)

    default_msg = f"[{version}] | initial release"
    commit_msg  = default_msg if args.yes else ask_commit_msg(default_msg)

    with DevSafetyGuard("deploy"):
        # Create orphan temporary branch
        temp_branch = f"temp-deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        log(f"Creating orphan branch: {temp_branch}", "INFO")
        run(f"git checkout --orphan {temp_branch}")

        # CRITICAL: Clear git index to ensure true orphan commit
        log("Clearing git index (ensures ZERO parent commits)...", "INFO")
        run("git rm -rf .", abort_on_error=False)

        # WIPE CLEAN (except protected items)
        log("Wiping working tree (except protected items)...", "INFO")
        log(f"Protected items: {protected_items}", "DEBUG")
        for item in os.listdir(SCRIPT_DIR):
            if item in protected_items:
                log(f"  PROTECTED: {item}", "DEBUG")
                continue
            path = os.path.join(SCRIPT_DIR, item)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                log(f"  REMOVED: {item}", "DEBUG")
            except Exception as e:
                log(f"Failed to remove {item}: {e}", "DEBUG")
        log("Working tree wiped.", "DEBUG")

        # COPY ONLY whitelisted files from dev
        log("=" * 70, "INFO")
        log("CRITICAL: Copying ONLY whitelisted files from dev", "INFO")
        log("This ensures ZERO non-public files on master", "INFO")
        log("=" * 70, "INFO")
        
        success = copy_whitelisted_files(dev_branch, whitelist)
        if not success:
            log("CRITICAL: File copy failed.", "ERROR")
            run(f"git checkout {dev_branch}", abort_on_error=False)
            run(f"git branch -D {temp_branch}", abort_on_error=False)
            sys.exit(1)

        # Create orphan commit (ZERO parents)
        log("Creating orphan commit (ZERO history)...", "INFO")
        run("git add .")
        run(f'git commit -m "{commit_msg}"')
        
        orphan_commit = get_current_commit()
        log(f"Orphan commit created: {orphan_commit}", "DEBUG")

        # Verify commit has ZERO parents
        ok, parents = run_ok(f"git log --pretty=%P -n 1 {orphan_commit}")
        if parents.strip():
            log(f"ERROR: Commit has parents: {parents}", "ERROR")
            log("This should be an orphan commit with ZERO parents!", "ERROR")
            sys.exit(1)
        log("Verified: Commit has ZERO parents (true orphan).", "INFO")

        # Force update master branch to point to orphan commit
        log(f"Updating {release_branch} ref to orphan commit...", "INFO")
        run(f"git branch -D {release_branch}", abort_on_error=False)  # delete old master
        run(f"git branch -m {release_branch}")  # rename temp to master

        # Force push
        log(f"Force-pushing to {release_remote}/{release_branch}...", "INFO")
        run(f"git push --force {release_remote} {release_branch}")

        log("", "INFO")
        log("=" * 70, "INFO")
        log("DEPLOY finished. Master history WIPED.", "INFO")
        log(f"Master now has EXACTLY 1 commit: {orphan_commit[:8]}", "INFO")
        log("Master contains ONLY whitelisted files.", "INFO")
        log("Previous commits are unreachable (will be GC'd).", "INFO")
        log("", "INFO")
        log("Other developers need to sync master with:", "INFO")
        log(f"  git fetch {release_remote}", "INFO")
        log(f"  git reset --hard {release_remote}/{release_branch}", "INFO")
        log("=" * 70, "INFO")

    log("DEPLOY finished.", "INFO")


def cmd_reset(cfg, args):
    release_branch = cfgget(cfg, "ReleaseBranch", "master")
    release_remote = cfgget(cfg, "ReleaseRemote", "origin")

    if not args.yes:
        print()
        print(f"  WARNING: --reset will OVERWRITE local {release_branch}.")
        print()
        ans = input("  Type YES to confirm: ").strip()
        if ans != "YES":
            log("Reset aborted.", "INFO")
            sys.exit(0)

    with DevSafetyGuard("reset"):
        log(f"Switching to {release_branch}...", "INFO")
        run(f"git checkout {release_branch}")

        log(f"Fetching {release_remote}/{release_branch}...", "INFO")
        run(f"git fetch {release_remote} {release_branch}")

        log(f"Hard reset to {release_remote}/{release_branch}...", "INFO")
        run(f"git reset --hard {release_remote}/{release_branch}")

    log("RESET finished.", "INFO")


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    global CURRENT_LOG_FILE

    cfg = load_and_sync_config()

    print("\n====================================================")
    print(f"  MAMBA SYNC TOOL v{SCRIPT_VER} | {cfgget(cfg, 'RemoteProjectName', 'PROJECT')}")
    print("====================================================\n")

    parser = argparse.ArgumentParser(
        description="MAMBA SYNC TOOL - maintains clean public master, preserves full dev history",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--zip",         action="store_true",
                        help="Create local whitelist ZIP")
    parser.add_argument("--full-backup", action="store_true",
                        help="Full backup (.git included)")
    parser.add_argument("--update",      action="store_true",
                        help="Update master (+1 commit, whitelisted files, ZERO dev history leak)")
    parser.add_argument("--release",     action="store_true",
                        help="--update + ZIPs + GitHub Release")
    parser.add_argument("--deploy",      action="store_true",
                        help="WIPE master history (orphan commit, use for cleanup)")
    parser.add_argument("--reset",       action="store_true",
                        help="Force pull master from GitHub")
    parser.add_argument("-y", "--yes",   action="store_true",
                        help="Skip all prompts")
    args = parser.parse_args()

    # Determine command string
    if args.full_backup:
        cmd_str = "--full-backup"
        cmd_filename = "sync--full-backup"
    elif args.zip:
        cmd_str = "--zip"
        cmd_filename = "sync--zip"
    elif args.update:
        cmd_str = "--update"
        cmd_filename = "sync--update"
    elif args.release:
        cmd_str = "--release"
        cmd_filename = "sync--release"
    elif args.deploy:
        cmd_str = "--deploy"
        cmd_filename = "sync--deploy"
    elif args.reset:
        cmd_str = "--reset"
        cmd_filename = "sync--reset"
    else:
        cmd_str = "(default dev sync)"
        cmd_filename = "sync--dev"

    # Setup logging with header
    log_dir = cfgget(cfg, "LogDir", "logs")
    os.makedirs(os.path.join(SCRIPT_DIR, log_dir), exist_ok=True)
    CURRENT_LOG_FILE = os.path.join(
        SCRIPT_DIR, log_dir,
        f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{cmd_filename}.log"
    )
    
    write_log_header(cmd_str, CURRENT_LOG_FILE)
    log(f"Log file: {CURRENT_LOG_FILE}", "DEBUG")

    version = resolve_version(cfg)
    log(f"Project version: {version}", "DEBUG")

    # Dispatch
    if args.full_backup:
        cmd_full_backup(cfg, version)
    elif args.zip:
        cmd_zip(cfg, version)
    elif args.update:
        cmd_update(cfg, version, args)
    elif args.release:
        cmd_release(cfg, version, args)
    elif args.deploy:
        cmd_deploy(cfg, version, args)
    elif args.reset:
        cmd_reset(cfg, args)
    else:
        cmd_dev_sync(cfg, version, args)


if __name__ == "__main__":
    main()