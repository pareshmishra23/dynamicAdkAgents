from __future__ import annotations

from app.config.h2jar import H2_VERSION, ensure_h2_jar


def main() -> None:
    jar = ensure_h2_jar()
    print(f"H2 {H2_VERSION} ready: {jar}")


if __name__ == "__main__":
    main()