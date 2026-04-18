# ops-console-git AUR Staging Folder

This folder mirrors the package files intended for the AUR repository.

Files to publish:

- `PKGBUILD`
- `.SRCINFO`

Typical workflow:

```bash
git clone ssh://aur@aur.archlinux.org/ops-console-git.git
cd ops-console-git
cp /path/to/your/source/repo/aur/ops-console-git/PKGBUILD .
cp /path/to/your/source/repo/aur/ops-console-git/.SRCINFO .
git add PKGBUILD .SRCINFO
git commit -m "Initial import"
git push
```
