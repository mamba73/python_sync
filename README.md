# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Advanced Dual-Repo & Clean History Automation.** Specifically designed to bridge the gap between private development and public production environments while maintaining absolute privacy for internal tools.

This tool enforces a strict **WhiteList** policy for public releases, ensuring that only necessary source files reach the public repository, while the **Private Dev** branch remains a full-featured workspace.

**Version**: 1.4.0  
**Author**: mamba

---
## 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| **WhiteList Purge** | Only allowed files (Plugin, csproj, sln, md, manifest) survive the release to Master. |
| **Changelog Auto-Gen** | Automatically generates ```CHANGELOG.md``` by parsing commits since the last version tag. |
| **History Flattening** | The ```--deploy``` command wipes master history for a clean, professional public appearance. |
| **Incremental Update** | The ```--update``` command adds a single clean commit to Master without losing previous version history. |
| **Safety First** | Includes mandatory directory verification, branch mismatch protection, and emergency backups. |
| **GH CLI Release** | Full integration with GitHub CLI for automated Tagging and Release creation with notes. |

---
## 📝 Usage

### 1. Standard Dev Sync (Private)
> ```python sync.py```
*Syncs all project files (including tools) to your private remote. Preserves uncommitted local work.*

### 2. Incremental Public Update
> ```python sync.py --update```
*Performs a WhiteList purge and adds ONE new commit to the public Master branch. Keeps existing history.*

### 3. Full Clean Release (Flattened)
> ```python sync.py --deploy```
*Wipes Master history, creates a single "Release vX.Y.Z" commit, and uploads a GitHub Release via GH CLI.*

### 4. Silent Mode (Auto-Confirm)
> ```python sync.py -y```
*Skips all prompts. Ideal for quick syncs or automated pipelines.*

### 5. Open Session Logs
> ```python sync.py -o```
*Opens the current session's log file in VS Code or your default text editor for debugging.*

---
## 📜 WhiteList (Master Branch Filter)
To ensure privacy, only these items are allowed to reach the Public Remote:
- ```Plugin/``` directory (Source files only)
- ```*.csproj``` and ```*.sln``` files
- ```manifest.xml``` and ```.gitignore```
- ```CHANGELOG.md```, ```README.md```, and other root ```*.md``` files
- ```LICENSE```

---
## 🛠️ Configuration (```config_sync.ini```)

```
[SETTINGS]
ProjectName = mamba.TorchDiscordSync
DevRemote = private
ReleaseRemote = origin
LogDir = logs
VSCodePath = c:\dev\VSCode\bin\code.cmd
```

---
## ☕ Support
If you like this project and want to support development:
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73)

*Developed by [mamba73](https://github.com/mamba73). Clean code, clean history.*
