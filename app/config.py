from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AppConfig:
    udp_port: int = 5140
    web_port: int = 8080
    max_memory_logs: int = 10_000
    log_dir: str = "./logs"
    keep_days: int = 3
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    write_to_file: bool = True
    udp_whitelist: List[str] = field(default_factory=list)
    websocket_token: Optional[str] = None

    @staticmethod
    def load(path: Path | str) -> "AppConfig":
        config_path = Path(path)
        if not config_path.exists():
            return AppConfig()

        with config_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return AppConfig(**data)


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def get_config() -> AppConfig:
    return AppConfig.load(CONFIG_PATH)
