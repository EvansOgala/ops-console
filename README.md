# Ops Console (Starter)

## Features

- Network Forensics tab:
  - live process/socket list
  - suspicious connection flagging
  - reverse DNS on double-click
- Update Orchestrator tab:
  - detect package managers
  - check available updates for pacman / flatpak / apt

## Run

```bash
cd /home/evans/Documents/ops-console
python3 main.py
```

## Optional

Install `psutil` for richer network/process insights:

```bash
pip install psutil
```

## Build AppImage

```bash
cd /home/evans/Documents/ops-console
python3 -m pip install --user pyinstaller
# also install appimagetool system-wide, or place it at ./tools/appimagetool.AppImage
./build-appimage.sh
```
