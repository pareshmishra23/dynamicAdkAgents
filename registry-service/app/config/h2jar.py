from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve

from app.config.settings import DEFAULT_JAR

H2_VERSION = "2.3.232"
H2_MIRROR = (
    "https://repo1.maven.org/maven2/com/h2database/h2/"
    f"{H2_VERSION}/h2-{H2_VERSION}.jar"
)


def ensure_h2_jar(dest: Path | None = None) -> Path:
    target = Path(dest) if dest else DEFAULT_JAR
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[h2] downloading {H2_MIRROR} -> {target}")
    urlretrieve(H2_MIRROR, str(target))
    return target