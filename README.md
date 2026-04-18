# Ops Console

GTK4 operations console for network connection inspection and update orchestration.

## Features

- Live process and socket list
- Suspicious external connection flagging
- Reverse DNS lookup on selected connections
- Update checks for pacman, flatpak, and apt
- Launch supported update commands in an available terminal emulator
- Light and dark GTK4 themes

## Runtime Dependencies

- Python 3
- GTK4
- PyGObject
- python-psutil
- Optional: `checkupdates` from `pacman-contrib` for richer pacman update checks
- A supported terminal emulator for update launch actions

On Arch Linux:

```bash
sudo pacman -S --needed python python-gobject gtk4 python-psutil xterm
```

## Run From Source

```bash
cd ~/Documents/ops-console
python3 main.py
```

## Packaging

This repository now includes an AUR-ready `ops-console-git` package:

- [PKGBUILD](./PKGBUILD)
- [.SRCINFO](./.SRCINFO)

To build it locally on Arch Linux:

```bash
cd ~/Documents/ops-console
makepkg -si
```

## Notes

- Update launch features depend on a terminal emulator and the relevant package manager being installed.
- Settings are stored in `~/.config/ops_console/settings.json`.

## License

MIT
