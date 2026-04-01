from __future__ import annotations

import argparse
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from . import __version__
from .config import (
    DEFAULT_CONF_DIR,
    DEFAULT_CONF_FILE,
    ConfigError,
    InterfaceConfig,
    configtest,
    load_all_configs,
    save_interface_config,
)
from . import tc

SERVICE_INSTALL_PATH = Path("/etc/systemd/system/alabofur.service")


def _print_err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _require_root_if_needed(needs_root: bool) -> None:
    if needs_root and hasattr(tc, "require_root"):
        tc.require_root()


def _ensure_deps():
    try:
        tc.install_dependencies()
    except Exception as exc:  # noqa: BLE001
        _print_err(str(exc))
        return False
    return True


def _systemctl(args: Iterable[str]) -> int:
    if shutil.which("systemctl") is None:
        _print_err("systemctl not found; systemd is required for service management.")
        return 1
    cmd = ["systemctl", *args]
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as exc:
        _print_err(exc.stderr or str(exc))
        return exc.returncode


def cmd_list(args: argparse.Namespace) -> int:
    interfaces = args.interfaces
    try:
        configs = load_all_configs()
    except ConfigError:
        configs = {}

    if not interfaces:
        interfaces = list(configs.keys())
    if not interfaces:
        _print_err("No interfaces configured; use `alabofur add <iface> <down> <up>`.")
        return 1

    for iface in interfaces:
        cfg = configs.get(iface)
        if cfg:
            print(f"[{iface}] configured: down={cfg.download_mbit}mbit up={cfg.upload_mbit}mbit ipv6={cfg.ipv6}")
        else:
            print(f"[{iface}] not in config; showing tc state")
        try:
            print(tc.show(iface))
        except Exception as exc:  # noqa: BLE001
            _print_err(f"{iface}: {exc}")
    return 0


def _apply_interfaces(target_ifaces: Optional[list[str]]) -> int:
    configs = load_all_configs()
    if target_ifaces:
        missing = [i for i in target_ifaces if i not in configs]
        if missing:
            raise ConfigError(f"Interfaces not in config: {', '.join(missing)}")
        selected = {k: v for k, v in configs.items() if k in target_ifaces}
    else:
        selected = configs

    for cfg in selected.values():
        tc.setup(cfg)
        print(f"applied {cfg.name}: down={cfg.download_mbit}mbit up={cfg.upload_mbit}mbit")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if not _ensure_deps():
        return 1
    try:
        return _apply_interfaces(args.interfaces)
    except ConfigError as exc:
        _print_err(str(exc))
        return 1
    except tc.TCError as exc:
        _print_err(str(exc))
        return 1


def cmd_add(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if not _ensure_deps():
        return 1
    cfg = InterfaceConfig(
        name=args.interface,
        download_mbit=args.download,
        upload_mbit=args.upload,
        ipv6=not args.ipv4_only,
    )
    save_interface_config(cfg)
    print(f"saved config {cfg.name} at {DEFAULT_CONF_DIR}")
    return cmd_apply(argparse.Namespace(interfaces=[cfg.name]))


def cmd_deny(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if not _ensure_deps():
        return 1
    cfg = InterfaceConfig(name=args.interface, download_mbit=1, upload_mbit=1, ipv6=True)
    save_interface_config(cfg)
    print(f"set {cfg.name} to minimal bandwidth (deny)")
    return cmd_apply(argparse.Namespace(interfaces=[cfg.name]))


def cmd_clear(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if not _ensure_deps():
        return 1
    try:
        tc.clear(args.interface)
        print(f"cleared shaping for {args.interface}")
        return 0
    except Exception as exc:  # noqa: BLE001
        _print_err(str(exc))
        return 1


def cmd_configtest(args: argparse.Namespace) -> int:
    try:
        configtest()
        print("config OK")
        return 0
    except ConfigError as exc:
        _print_err(str(exc))
        return 1


def _install_service(force: bool = False) -> None:
    import importlib.resources

    with importlib.resources.open_text("alabofur", "alabofur.service") as f:
        content = f.read()
    bin_path = shutil.which("alabofur") or "/usr/bin/alabofur"
    content = content.replace("@ALABOFUR_BIN@", bin_path)
    if SERVICE_INSTALL_PATH.exists() and not force:
        raise RuntimeError(f"{SERVICE_INSTALL_PATH} already exists (use --force to overwrite)")
    SERVICE_INSTALL_PATH.write_text(content)
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "alabofur.service"], check=False)


def cmd_install_service(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if not _ensure_deps():
        return 1
    try:
        _install_service(force=args.force)
        print(f"installed {SERVICE_INSTALL_PATH}")
        return 0
    except Exception as exc:  # noqa: BLE001
        _print_err(str(exc))
        return 1


def cmd_remove_service(args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    if SERVICE_INSTALL_PATH.exists():
        subprocess.run(["systemctl", "disable", "alabofur.service"], check=False)
        SERVICE_INSTALL_PATH.unlink()
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        print("service removed")
    else:
        print("service not installed")
    return 0


def cmd_service_action(action: str, args: argparse.Namespace) -> int:
    _require_root_if_needed(True)
    return _systemctl([action, "alabofur.service"])


def cmd_service_run(args: argparse.Namespace) -> int:
    # for systemd ExecStart
    try:
        configtest()
        return _apply_interfaces(args.interfaces)
    except Exception as exc:  # noqa: BLE001
        _print_err(str(exc))
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alabofur",
        description="Simple tc-based bandwidth shaper (ufw-like UX)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="show current tc state for configured interfaces")
    p_list.add_argument("interfaces", nargs="*", help="interfaces to show")
    p_list.set_defaults(func=cmd_list)

    p_apply = sub.add_parser("apply", help="apply limits from config")
    p_apply.add_argument("interfaces", nargs="*", help="interfaces to apply (default: all)")
    p_apply.set_defaults(func=cmd_apply)

    p_add = sub.add_parser("add", help="add/update interface limits")
    p_add.add_argument("interface")
    p_add.add_argument("download", type=int, help="download limit in mbit")
    p_add.add_argument("upload", type=int, help="upload limit in mbit")
    p_add.add_argument("--ipv4-only", action="store_true", help="disable ipv6 filters")
    p_add.set_defaults(func=cmd_add)

    p_deny = sub.add_parser("deny", help="set interface to near-zero bandwidth")
    p_deny.add_argument("interface")
    p_deny.set_defaults(func=cmd_deny)

    p_clear = sub.add_parser("clear", help="remove shaping rules for interface")
    p_clear.add_argument("interface")
    p_clear.set_defaults(func=cmd_clear)

    p_ct = sub.add_parser("configtest", help="validate configuration files")
    p_ct.set_defaults(func=cmd_configtest)

    p_isvc = sub.add_parser("install-service", help="install systemd service")
    p_isvc.add_argument("--force", action="store_true", help="overwrite existing unit")
    p_isvc.set_defaults(func=cmd_install_service)

    p_rs = sub.add_parser("remove-service", help="remove systemd service")
    p_rs.set_defaults(func=cmd_remove_service)

    for action in ["start", "stop", "restart", "status"]:
        p = sub.add_parser(action, help=f"{action} systemd service")
        p.set_defaults(func=lambda a, act=action: cmd_service_action(act, a))

    p_srv = sub.add_parser("service-run", help=argparse.SUPPRESS)
    p_srv.add_argument("interfaces", nargs="*", help="interfaces to apply (default: all)")
    p_srv.set_defaults(func=cmd_service_run)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
