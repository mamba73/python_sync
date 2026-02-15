# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Professional Dual-Repo & Changelog Automation.** This utility is designed for developers who maintain a private repository for active development and a public repository for official releases.

**Version**: 1.9.1  
**Author**: mamba

---
## 🚀 Features

| Feature | Description |
| :--- | :--- |
| **Interactive Setup** | Automatically detects project root and guides you through the initial ```config_sync.ini``` generation. |
| **Smart Versioning** | Features auto-increment logic with a manual override prompt. Version is synced across Config, Readme, and Manifest. |
| **WhiteList Purge** | Guarantees privacy by physically removing any file not explicitly allowed on the public branch during sync. |
| **Auto-Changelog** | Generates professional ```CHANGELOG.md``` entries by parsing git commits since the last tag. |
| **Secure Sync Engine** | Uses a temporary branch strategy to prevent Master history from overwriting or deleting local Dev files. |
| **Flattened Release** | Provides a ```--deploy``` option to wipe public history for a clean, single-commit professional appearance. |

---
## 📝 Usage

### 1. Daily Development Sync
> ```python sync.py -y```
*Syncs all files to your private remote. In auto-mode (```-y```), it increments the version and commits automatically.*

### 2. Incremental Public Update
> ```python sync.py --update```
*Updates Master branch with a single clean commit. Updates changelog and purges private files without losing Master history.*

### 3. Full Flattened Release
> ```python sync.py --deploy```
*Wipes public history, creates a fresh Release commit, and uploads a GitHub Release with notes via GH CLI.*

### 4. Backups & Archiving
> ```python sync.py --full-backup```
*Creates a full timestamped ZIP of the project in the parent directory, named by project and version.*

---
## 🛠️ Configuration (```config_sync.ini```)

The configuration is "self-healing" and will automatically add missing fields.

```
[SETTINGS]
LocalFolderName = YourLocalFolder
RemoteProjectName = PublicProjectName
DefaultVersion = 1.9.1
DevRemote = origin
ReleaseRemote = origin
DevBranch = dev
ReleaseBranch = master
ReleaseWhiteList = Plugin/, manifest.xml, .gitignore, LICENSE, CHANGELOG.md, .*\.csproj$, .*\.sln$, .*\.md$
KeepLogsDays = 7
```

---
## ☕ Support
If this tool saved you time, consider supporting further development:
[Buy Me a Coffee ☕](https://buymeacoffee.com)

*Developed by [mamba73](https://github.com). Automate more, worry less.*
