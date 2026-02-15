# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Professional Dual-Repo & Changelog Automation.** This utility is designed for developers who maintain a private repository for active development and a public repository for official releases.

**Version**: 1.9.5  
**Author**: mamba

---
## 🚀 Features

| Feature | Description |
| :--- | :--- |
| **Interactive Root Setup** | Automatically detects your project folder and locks operations to that specific directory for maximum safety. |
| **Dual-Mode Archiving** | Separate logic for ```--full-backup``` (parent dir, all files) and ```--zip``` (local dir, whitelisted only). |
| **Smart Versioning** | Auto-increment logic with manual override. Syncs version across Config, Readme, and Manifest files. |
| **Clean Master Sync** | Uses temporary branch isolation to update Master without risk of deleting or overwriting local Dev files. |
| **WhiteList Filter** | Physically removes any file/folder not explicitly allowed on the public branch during the release process. |
| **Auto-Changelog** | Parses git history since the last tag to generate professional ```CHANGELOG.md``` entries. |

---
## 📝 Usage

### 1. Daily Development Sync
> ```python sync.py -y```
*Automated sync to your private remote. Increments version and commits using "auto sync" message.*

### 2. Full Project Backup
> ```python sync.py --full-backup```
*Creates a complete ZIP archive of the entire project in the ```../``` (parent) directory.*

### 3. Local Release Preview (ZIP)
> ```python sync.py --zip```
*Creates a local ZIP in the project root containing ONLY whitelisted files. Perfect for manual distribution.*

### 4. Incremental Public Update
> ```python sync.py --update```
*Updates Master branch with a single clean commit. Updates changelog and purges private files.*

### 5. Full Flattened Release
> ```python sync.py --deploy```
*Wipes Master history, creates a fresh Release commit, and uploads a GitHub Release via GH CLI.*

---
## 🛠️ Configuration (```config_sync.ini```)

```
[SETTINGS]
LocalFolderName = YourProjectFolder
RemoteProjectName = PublicProjectName
DefaultVersion = 1.9.3
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
