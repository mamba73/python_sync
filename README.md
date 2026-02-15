# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Professional Dual-Repo & Changelog Automation.** This utility is designed for developers who maintain a private repository for active development and a public repository for official releases.

**Version**: 1.6.0  
**Author**: mamba

---
## 🚀 Features


| Feature | Description |
| :--- | :--- |
| **Modular Config** | Fully portable! Use the same script across multiple projects by editing ```config_sync.ini```. |
| **WhiteList Purge** | Guarantees privacy by physically removing any file not explicitly allowed on the public branch. |
| **Auto-Changelog** | Generates professional ```CHANGELOG.md``` entries automatically from your commit history. |
| **Validation Engine** | Prevents accidental execution if the project name or directory doesn't match the configuration. |
| **Log Management** | Automatically cleans up old session logs based on your defined retention policy. |
| **Clean History** | Provides a "Flattened" history option for public repos, hiding messy dev commits. |

---
## 📝 Usage

### 1. Daily Development Sync
> ```python sync.py -y```
*Syncs all files to your private remote with an automatic commit message.*

### 2. Incremental Public Update
> ```python sync.py --update```
*Generates changelog, purges private files, and adds one clean commit to the public Master branch.*

### 3. Full Flattened Release
> ```python sync.py --deploy```
*Wipes public history for a fresh start, creates a GitHub Release, and uploads notes via GH CLI.*

### 4. Open Session Logs
> ```python sync.py -o```
*Instantly opens the current log file in VS Code or your default editor.*

---
## 🛠️ Setup & Configuration

Upon first run, the script generates a ```config_sync.ini```. You **must** update the ```ProjectName``` to match your folder name.

```
[SETTINGS]
ProjectName = YourProjectFolderName
DevRemote = private
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
