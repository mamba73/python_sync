"""
# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Dual-Repo Automation Utility.** Specifically designed to handle synchronization between private development and public production environments.

This tool maintains two distinct workflows: a **Private Dev** workflow that tracks all files (including documentation and tools), and a **Public Release** workflow that strips sensitive or unnecessary files before pushing to the public repository.

**Version**: 1.1.0  
**Author**: mamba

---
## 🚀 Features

| Feature | Description |
| :--- | :--- |
| **Private Sync** | Pushes everything (including scripts and tools) to the private remote. |
| **Public Release** | Squash merges ```dev[/code] to ```master[/code] while stripping tools, scripts, and build folders. |
| **Auto-Conflict Fix** | Uses ```-X theirs[/code] to ensure dev branch always overwrites master. |
| **Zip Archiving** | Creates Source backups or Release (DLL) packages automatically. |
| **GH CLI Deploy** | Automated Release ZIP creation and GitHub Release upload in one step. |

---
## 📝 Usage

### 1. Dev Sync (Private)
> python sync.py
*Syncs all files to your private dev branch. Updates README version automatically.*

### 2. Manual Backup (Source ZIP)
> python sync.py --zip
*Creates a ZIP archive of your source code based on predefined file list.*

### 3. Full Deploy (Public Release)
> python sync.py --deploy
*Master squash + DLL Release ZIP + GitHub Release upload via GH CLI.*

---
## 🛠️ Configuration (```config_sync.ini[/code])

```
[SETTINGS]
DevRemote = private
ReleaseRemote = origin
ProjectName = mamba.TorchDiscordSync
ScriptVersion = 1.1.0
LogDir = logs
[/code]

---
## 🤝 Support
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73)
"""