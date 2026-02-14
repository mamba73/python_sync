"""
# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Dual-Repo Automation Utility.** Specifically designed to handle synchronization between private development and public production environments.

This tool maintains two distinct workflows: a **Private Dev** workflow that tracks all files (including documentation and tools), and a **Public Release** workflow that strips sensitive or unnecessary files before pushing to the public repository.

**Version**: 1.0.5  
**Author**: mamba

---
## 🚀 Features

| Feature | Description |
| :--- | :--- |
| **Private Sync** | Pushes everything (including ```doc/``` and scripts) to the private remote. |
| **Public Release** | Squash merges ```dev``` to ```master``` while stripping ```doc/```, ```sync.py```, and build folders. |
| **Auto-Conflict Fix** | Uses ```-X theirs``` to ensure dev branch always overwrites master. |
| **GH CLI Deploy** | Automated ZIP creation and GitHub Release upload in one step. |

---
## 📝 Usage

### 1. Dev Sync (Private)
> python sync.py
*Syncs all files to your private dev branch.*

### 2. Full Deploy (Public)
> python sync.py --deploy
*Master squash + ZIP archive + GitHub Release upload.*

---
## 🛠️ Configuration (```config_sync.ini```)

```ini
[SETTINGS]
DevRemote = private
ReleaseRemote = origin
ProjectName = mambaTorchDiscordSync
ScriptVersion = 1.0.5
```

---
## 🤝 Support
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73)
"""