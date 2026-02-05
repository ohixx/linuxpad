pkgname=linuxpad
pkgver=1.0.0
pkgrel=1
pkgdesc="Simple Soundpadik for linux pipiware (pipitka nahuy)"
arch=('any')
url="https://github.com/ohixx/linuxpad"
license=('MIT')
depends=(
    'python'
    'python-pyqt6'
    'pipewire'
    'pipewire-pulse'
)
optdepends=(
    'python-pynput: Global hotkey support'
)
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    cd "$srcdir/$pkgname-$pkgver"

    install -Dm755 linuxpad.py "$pkgdir/usr/bin/linuxpad"
    install -Dm644 linuxpad.desktop "$pkgdir/usr/share/applications/linuxpad.desktop"
}
