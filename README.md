# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Dual-Repo Automation Utility.** Specifically designed to handle synchronization between private development and public production environments.

This tool maintains two distinct workflows: a **Private Dev** workflow that tracks all files (including documentation and tools), and a **Public Release** workflow that strips sensitive or unnecessary files before pushing to the public repository.

**Version**: 1.1.2  
**Author**: mamba

---
## 🚀 Features

| Feature | Description |
| :--- | :--- |
| **Private Sync** | Pushes everything (including scripts and tools) to the private remote. |
| **Public Release** | Squash merges ```dev``` to ```master``` while stripping tools, scripts, and build folders. |
| **Auto-Conflict Fix** | Uses ```-X theirs``` to ensure dev branch always overwrites master. |
| **Zip Archiving** | Creates Source backups or Release (DLL) packages automatically. |
| **Full Backup** | Creates a timestamped ```.zip``` of the entire project folder in the parent directory. |
| **GH CLI Deploy** | Automated Release ZIP creation and GitHub Release upload in one step. |

---
## 📝 Usage

### 1. Dev Sync (Private)
> ```python sync.py```
*Syncs all files to your private dev branch. Updates README version automatically.*

### 2. Manual Backup (Source ZIP)
> ```python sync.py --zip```
*Creates a ZIP archive of your source code based on predefined file list.*

### 3. Full Project Backup
> ```python sync.py --full-backup```
*Creates a full archive ```[timestamp]_[version]_FULL_mambaTDS_[branch].zip``` in the parent folder.*

### 4. Full Deploy (Public Release)
> ```python sync.py --deploy```
*Master squash + DLL Release ZIP + GitHub Release upload via GH CLI.*

---
## 🛠️ Configuration (```config_sync.ini```)

```
[SETTINGS]
DevRemote = private
ReleaseRemote = origin
ProjectName = mamba.TorchDiscordSync
ScriptVersion = 1.1.2
LogDir = logs
```

---
## ☕ Support
If you like this project and want to support development:
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73)

*Developed by [mamba73](https://github.com/mamba73). Feel free to submit issues or pull requests!*