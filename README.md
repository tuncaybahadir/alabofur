# alabofur

Simple ufw-like CLI to cap upload/download speeds using Linux `tc`. Inspired by wondershaper; ships with a systemd service so limits persist across reboot. Language: English.

## Supported distributions
- Ubuntu 20.04+ (deb, uses `iproute2`, `kmod`)
- Debian 8+ (deb)
- Fedora 36+ (rpm, `iproute`/`kmod`)
- RHEL/CentOS/Alma/Rocky 8+ (rpm)
- openSUSE Leap/Tumbleweed (rpm, `iproute2`, `kmod`)
- Arch/Manjaro (pacman, `iproute2`, `kmod`)

## Installation from source
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade build
python3 -m build
pip install dist/alabofur-0.1.0-py3-none-any.whl
```

Install and enable the service:
```bash
sudo alabofur install-service
sudo systemctl start alabofur
```

### Debian/Ubuntu (deb) and RPM packaging
Build artifacts via `python3 -m build`; then package with `fpm` or your distro tooling:
```bash
fpm -s python -t deb dist/alabofur-0.1.0-py3-none-any.whl
fpm -s python -t rpm dist/alabofur-0.1.0-py3-none-any.whl
```
For Launchpad upload, use the sdist `dist/alabofur-0.1.0.tar.gz`. For GitHub Releases, attach the wheel and sdist.

## Configuration
Default file: `/etc/alabofur/alabofur.conf`. Additional per-interface files: `/etc/alabofur/*.conf`.
Example:
```ini
[eth0]
download_mbit = 50
upload_mbit = 10
ipv6 = true

[wlan0]
download_mbit = 20
upload_mbit = 5
```

## Usage
```bash
sudo alabofur add eth0 50 10      # apply 50/10 mbit to eth0
sudo alabofur list                # show tc state
sudo alabofur deny wlan0          # throttle wlan0 to ~1 mbit
sudo alabofur clear eth0          # remove shaping
sudo alabofur configtest          # validate configuration
sudo alabofur install-service     # install systemd unit
sudo systemctl restart alabofur   # restart service
```

## Man page
Available via `man alabofur` once installed. From source:
```bash
sudo install -D -m 0644 alabofur/man/alabofur.1 /usr/share/man/man1/alabofur.1
sudo mandb
```

## Notes
- Requires `tc`, `ip`, `modprobe`, and `systemd`. The CLI auto-installs `iproute2/iproute` and `kmod` via apt/dnf/yum/zypper/pacman when missing (root needed).
- IPv6 filters are enabled by default; use `--ipv4-only` to disable.

## Maintainer
Tuncay Bahadır — <tuncaybahadir@protonmail.com>
