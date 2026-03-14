# MAMBA SYNC TOOL (sync.py)

---
**NOTE: Professional Dev / Release Automation Tool**

**Tool Version**: 1.16.1  
**Author**: mamba

---
## 🔢 Versioning Rules

- `sync.py` version ≠ project version
- Project version priority:
  1. `manifest.xml` → `<Version>`
  2. `DefaultVersion` from `config_sync.ini` (fallback)

The tool will always report in DEBUG output which source was used.

---
## 🚀 Features

| Feature | Description |
|------|------------|
| Default Dev Sync | Running without parameters syncs DEV branch |
| Config-Driven | No hardcoded paths, whitelist, or patterns |
| Self-Healing Config | Missing config keys are auto-added |
| README Version Pattern | Version replacement pattern configurable |
| DEV Changelog | Generates CHANGELOG_DEV.md (not public) |
| Strict Whitelist ZIP | ZIP contents controlled via config |
| Clean Master Law | Public master never inherits dev history |
| Controlled Debug | Detailed git debug, limited ZIP noise |

---
## 📝 Usage

### Default DEV Sync
`python sync.py`

### Automatic DEV Sync
`python sync.py -y`

### Local ZIP Only
`python sync.py --zip`

### Public Update
`python sync.py --update`

### Public Release
`python sync.py --release`

### Destructive Deploy
`python sync.py --deploy`

---
## 🛠 Configuration Notes

Key options in `config_sync.ini`:

- `DefaultVersion` – project fallback version
- `ReadmeVersionPattern` – regex for README replacement
- `ReleaseWhiteList` – controls ZIP and public content
- `BackupFormat` – naming convention for all artifacts
- `KeepLogsDays` – log cleanup retention
- `BuildStagingDir` / `BinaryStagingDir` – binary packaging

---
## ☕ Support
If this tool saved you time, consider supporting further development.
[Buy Me a Coffee ☕](https://buymeacoffee.com/mamba73) 

*Developed by [mamba](https://github.com/mamba73). Automate more, worry less.*
