import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

DEFAULT_CONF_DIR = Path("/etc/alabofur")
DEFAULT_CONF_FILE = DEFAULT_CONF_DIR / "alabofur.conf"


@dataclass
class InterfaceConfig:
    name: str
    download_mbit: int
    upload_mbit: int
    ipv6: bool = True

    @property
    def download_kbit(self) -> int:
        return self.download_mbit * 1000

    @property
    def upload_kbit(self) -> int:
        return self.upload_mbit * 1000


class ConfigError(Exception):
    """Raised when configuration is invalid."""


def _parse_config(path: Path) -> Dict[str, InterfaceConfig]:
    parser = configparser.ConfigParser()
    parser.read(path)
    if not parser.sections():
        raise ConfigError(f"{path} has no interface sections")

    configs: Dict[str, InterfaceConfig] = {}
    for section in parser.sections():
        dl = parser.getint(section, "download_mbit", fallback=None)
        ul = parser.getint(section, "upload_mbit", fallback=None)
        ipv6 = parser.getboolean(section, "ipv6", fallback=True)
        if dl is None or ul is None:
            raise ConfigError(
                f"{path}: section [{section}] must define download_mbit and upload_mbit"
            )
        configs[section] = InterfaceConfig(section, dl, ul, ipv6)
    return configs


def load_all_configs(conf_dir: Path = DEFAULT_CONF_DIR) -> Dict[str, InterfaceConfig]:
    """Load default config plus any *.conf under conf_dir."""
    paths: List[Path] = []
    if DEFAULT_CONF_FILE.exists():
        paths.append(DEFAULT_CONF_FILE)
    if conf_dir.exists():
        paths.extend(sorted(p for p in conf_dir.glob("*.conf") if p != DEFAULT_CONF_FILE))
    if not paths:
        raise ConfigError(f"No config files found in {conf_dir}")

    merged: Dict[str, InterfaceConfig] = {}
    for path in paths:
        merged.update(_parse_config(path))
    return merged


def save_interface_config(cfg: InterfaceConfig, dir_path: Path = DEFAULT_CONF_DIR) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{cfg.name}.conf"
    parser = configparser.ConfigParser()
    parser[cfg.name] = {
        "download_mbit": str(cfg.download_mbit),
        "upload_mbit": str(cfg.upload_mbit),
        "ipv6": str(cfg.ipv6).lower(),
    }
    with path.open("w") as f:
        parser.write(f)
    return path


def configtest(conf_dir: Path = DEFAULT_CONF_DIR) -> None:
    errors: List[str] = []
    for path in sorted(conf_dir.glob("*.conf")):
        try:
            _parse_config(path)
        except ConfigError as exc:
            errors.append(str(exc))
    if DEFAULT_CONF_FILE.exists():
        try:
            _parse_config(DEFAULT_CONF_FILE)
        except ConfigError as exc:
            errors.append(str(exc))
    if errors:
        raise ConfigError("; ".join(errors))
