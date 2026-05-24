pkgname=ops-console-git
pkgver=0.r0.g0000000
pkgrel=1
pkgdesc="GTK4 operations console for network inspection and update checks"
arch=('x86_64')
url="https://github.com/EvansOgala/ops-console"
license=('MIT')
depends=(
  'glibc'
)
makedepends=(
  'git'
  'python'
  'python-gobject'
  'gtk4'
  'python-psutil'
)
optdepends=(
  'pacman-contrib: checkupdates support on pacman systems'
  'flatpak: Flatpak update checks'
  'xterm: fallback terminal for launching updates'
)
provides=('ops-console')
conflicts=('ops-console')
options=('!strip' '!debug')
source=("$pkgname::git+https://github.com/EvansOgala/ops-console.git")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/$pkgname"
  printf "0.r%s.g%s" \
    "$(git rev-list --count HEAD)" \
    "$(git rev-parse --short HEAD)"
}

build() {
  cd "$srcdir/$pkgname"
  python -c 'import PyInstaller' || {
    echo "PyInstaller is required. Install it before building this package." >&2
    return 1
  }
  python -m PyInstaller OpsConsole.spec --noconfirm --clean
}

package() {
  cd "$srcdir/$pkgname"

  local bundle_dir="$srcdir/$pkgname/dist/OpsConsole"
  if [[ ! -x "$bundle_dir/OpsConsole" ]]; then
    echo "Missing PyInstaller bundle: build() did not create dist/OpsConsole." >&2
    return 1
  fi

  install -d "$pkgdir/opt/ops-console" "$pkgdir/usr/bin"
  cp -a "$bundle_dir/." "$pkgdir/opt/ops-console/"
  ln -s /opt/ops-console/OpsConsole "$pkgdir/usr/bin/org.evans.OpsConsole"

  install -Dm644 org.evans.OpsConsole.desktop \
    "$pkgdir/usr/share/applications/org.evans.OpsConsole.desktop"
  install -Dm644 org.evans.OpsConsole.metainfo.xml \
    "$pkgdir/usr/share/metainfo/org.evans.OpsConsole.metainfo.xml"
  install -Dm644 org.evans.OpsConsole.svg \
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/org.evans.OpsConsole.svg"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
