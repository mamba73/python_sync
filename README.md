# MAMBA SYNC TOOL (sync.py)

---
**NOTE: This tool is designed specifically for Mamba's plugin development workflow.** It automates the synchronization between private development and public release repositories.

An advanced Python-based CI/CD utility for Space Engineers plugin developers who maintain dual-repository setups (Private Dev vs. Public Origin).

This tool ensures that your public repository remains clean, containing only production-ready code with a simplified history, while your private repository tracks every single granular change during the development process.

**Language**: Python 3.8+  
**Dependencies**: Git, GitHub CLI (gh)  
**Author**: mamba  
**Version**: 1.0.3

---
## 🚀 Tool Capabilities: Active development

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Dev Sync** | ✅ Done | Auto-stages changes and pushes to private remote. |
| **Change Logging** | ✅ Done | Captures diff stats and file lists for every commit. |
| **Squash Release** | ✅ Done | Merges dev to master as a single clean commit. |
| **Automated ZIP** | ✅ Done | Creates timestamped distribution packages. |
| **GitHub Deployment** | ✅ Done | Uploads ZIP assets directly to GitHub Releases. |
| **Log Management** | ✅ Done | Automatic cleanup of old logs (default 7 days). |
| **Script Stripping** | ✅ Done | Automatically prevents tool scripts from leaking to public master. |

---
## 🌟 Key Workflows

### 💻 Private Development (```python sync.py```)
This is your daily driver. It streamlines the backup of your work.
- **Smart Staging:** Automatically runs ```git add .```.
- **Change Detection:** Summarizes exactly what was modified before asking for a message.
- **Auto-Versioned Logs:** Saves a detailed log of the session in the ```/logs``` directory.

### 🛡️ Clean Master Release (```--release```)
Perfect for public-facing repositories.
- **History Squashing:** Uses ```git merge --squash``` to hide your "messy" development history.
- **Public Cleanup:** Removes the ```sync.py``` and ```config.ini``` files from the master branch commit automatically.

### 📦 Full Deploy (```--deploy```)
The complete pipeline in one command.



1. Updates the project version and README.
2. Performs the Squash Release to master.
3. Generates a distribution ZIP.
4. Uses **GitHub CLI** to create a formal release and upload the ZIP.

---
## 🛠️ Setup & Configuration

### Prerequisites
1. **GitHub CLI**: Install via [cli.github.com] and run ```gh auth login```.
2. **Remotes**: Ensure you have two remotes configured:
   - ```private```: Your private dev repo.
   - ```origin```: Your public release repo.

### Config File (```config_sync.ini```)
Generated on first run. Allows you to change paths, project names, and log retention.

```ini
[SETTINGS]
LogDir = logs
ProjectName = mambaTorchDiscordSync
DevRemote = private
ReleaseRemote = origin
KeepLogsDays = 7
ScriptVersion = 1.0.3
```

---
## 📝 Command Summary

| Flag | Description |
| :--- | :--- |
| ```--release``` | Squash merge dev -> master & push code. |
| ```--zip```     | Generate a distribution ZIP archive. |
| ```--deploy```  | **Release + ZIP + GitHub Release Upload**. |
| ```-y, --yes``` | Skip all confirmation prompts. |
| ```-o, --open```| Open the log file in VS Code after completion. |

---
## 🤝 Contributing
Feel free to fork and adapt this script for your own Torch or SE projects.

---
## ☕ Support
If this automation saved you time:
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73)

*Developed by [mamba73](https://github.com/mamba73).*
