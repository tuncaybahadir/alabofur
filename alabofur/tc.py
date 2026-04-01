import os
import shutil
import subprocess
from typing import List

from .config import InterfaceConfig


class TCError(RuntimeError):
    pass


def _ensure_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise TCError(f"Required binary not found: {name}")


def install_dependencies() -> None:
    """Attempt to install tc/ip/modprobe via system package manager."""
    missing = [b for b in ("tc", "ip", "modprobe") if shutil.which(b) is None]
    if not missing:
        return

    if shutil.which("apt"):
        pkgs = ["iproute2", "kmod"]
        cmd = ["apt", "update"]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = ["apt", "install", "-y", *pkgs]
    elif shutil.which("apt-get"):
        pkgs = ["iproute2", "kmod"]
        cmd = ["apt-get", "update"]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = ["apt-get", "install", "-y", *pkgs]
    elif shutil.which("dnf"):
        pkgs = ["iproute", "kmod"]
        cmd = ["dnf", "install", "-y", *pkgs]
    elif shutil.which("yum"):
        pkgs = ["iproute", "kmod"]
        cmd = ["yum", "install", "-y", *pkgs]
    elif shutil.which("zypper"):
        pkgs = ["iproute2", "kmod"]
        cmd = ["zypper", "--non-interactive", "install", *pkgs]
    elif shutil.which("pacman"):
        pkgs = ["iproute2", "kmod"]
        cmd = ["pacman", "--noconfirm", "-S", *pkgs]
    else:
        raise TCError("Package manager not found; install iproute2/iproute and kmod manually.")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise TCError(f"Failed to install dependencies ({' '.join(cmd)}): {exc}") from exc


def _run(cmd: List[str], check: bool = True, allow_fail: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        if allow_fail:
            return exc
        raise TCError(f"{' '.join(cmd)} failed: {exc.stderr.strip() or exc}") from exc


def require_root() -> None:
    if os.geteuid() != 0:
        raise TCError("This command must be run as root.")


def clear(iface: str) -> None:
    require_root()
    _ensure_binary("tc")
    _ensure_binary("ip")

    ifb = f"ifb-{iface}"
    _run(["tc", "qdisc", "del", "dev", iface, "root"], check=False, allow_fail=True)
    _run(["tc", "qdisc", "del", "dev", iface, "ingress"], check=False, allow_fail=True)
    _run(["tc", "qdisc", "del", "dev", ifb, "root"], check=False, allow_fail=True)
    _run(["ip", "link", "set", "dev", ifb, "down"], check=False, allow_fail=True)
    _run(["ip", "link", "del", ifb, "type", "ifb"], check=False, allow_fail=True)


def setup(cfg: InterfaceConfig) -> None:
    require_root()
    _ensure_binary("tc")
    _ensure_binary("ip")
    _ensure_binary("modprobe")

    iface = cfg.name
    ifb = f"ifb-{iface}"
    clear(iface)

    _run(["modprobe", "ifb"])
    _run(["ip", "link", "add", ifb, "type", "ifb"])
    _run(["ip", "link", "set", ifb, "up"])

    up = f"{cfg.upload_kbit}kbit"
    down = f"{cfg.download_kbit}kbit"

    # Egress (upload)
    _run(["tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "htb", "default", "30"])
    _run(["tc", "class", "add", "dev", iface, "parent", "1:", "classid", "1:1", "htb", "rate", up, "ceil", up])
    _run(["tc", "class", "add", "dev", iface, "parent", "1:1", "classid", "1:30", "htb", "rate", up, "ceil", up])
    _run(["tc", "qdisc", "add", "dev", iface, "parent", "1:30", "handle", "30:", "sfq", "perturb", "10"])

    # Ingress (download) via ifb
    _run(["tc", "qdisc", "add", "dev", iface, "handle", "ffff:", "ingress"])
    _run(["tc", "filter", "add", "dev", iface, "parent", "ffff:", "protocol", "ip", "prio", "50", "u32", "match", "u32", "0", "0", "flowid", "1:1", "action", "mirred", "egress", "redirect", "dev", ifb])
    if cfg.ipv6:
        _run(["tc", "filter", "add", "dev", iface, "parent", "ffff:", "protocol", "ipv6", "prio", "55", "u32", "match", "u32", "0", "0", "flowid", "1:1", "action", "mirred", "egress", "redirect", "dev", ifb])

    _run(["tc", "qdisc", "add", "dev", ifb, "root", "handle", "2:", "htb", "default", "20"])
    _run(["tc", "class", "add", "dev", ifb, "parent", "2:", "classid", "2:1", "htb", "rate", down, "ceil", down])
    _run(["tc", "class", "add", "dev", ifb, "parent", "2:1", "classid", "2:20", "htb", "rate", down, "ceil", down])
    _run(["tc", "qdisc", "add", "dev", ifb, "parent", "2:20", "handle", "20:", "sfq", "perturb", "10"])


def show(iface: str) -> str:
    _ensure_binary("tc")
    result = _run(["tc", "-s", "qdisc", "show", "dev", iface], check=False)
    return (result.stdout or result.stderr).strip()
