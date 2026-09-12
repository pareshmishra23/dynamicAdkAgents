from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_JAR = BASE_DIR / "third_party" / "h2.jar"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    h2_url: str = _env("H2_URL", "jdbc:h2:file:./data/registry;AUTO_SERVER=TRUE")
    h2_user: str = _env("H2_USER", "sa")
    h2_password: str = _env("H2_PASSWORD", "")
    h2_jar_path: Path = Path(_env("H2_JAR_PATH", str(DEFAULT_JAR)))
    host: str = _env("HOST", "127.0.0.1")
    port: int = int(_env("PORT", "8000"))