from __future__ import annotations

import sys
import time
from typing import TextIO

_COLORS = {
    "think": "\033[36m",
    "pointer": "\033[35m",
    "act": "\033[33m",
    "verify": "\033[32m",
    "critic": "\033[31m",
    "escalate": "\033[1;31m",
    "decide": "\033[1;34m",
}
_RESET = "\033[0m"


class ThinkTracer:
    """Print the pool's reasoning trail so humans can audit what each agent
    points at, executes, and why — mirroring how coding agents show their work."""

    def __init__(self, enabled: bool = True, stream: TextIO | None = None) -> None:
        self._enabled = enabled
        self._stream = stream or sys.stdout
        self._steps: list[str] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def steps(self) -> tuple[str, ...]:
        return tuple(self._steps)

    def emit(self, label: str, message: str) -> str:
        step = f"[{label}] {message}"
        self._steps.append(step)
        if self._enabled:
            color = _COLORS.get(label, _RESET)
            print(f"{color}{step}{_RESET}", file=self._stream, flush=True)
        return step

    def think(self, message: str) -> None:
        self.emit("think", message)

    def pointer(self, message: str) -> None:
        self.emit("pointer", message)

    def act(self, message: str) -> None:
        self.emit("act", message)

    def verify(self, message: str) -> None:
        self.emit("verify", message)

    def critic(self, message: str) -> None:
        self.emit("critic", message)

    def escalate(self, message: str) -> None:
        self.emit("escalate", message)

    def decide(self, message: str) -> None:
        self.emit("decide", message)

    def runtime_ms(self, started: float) -> str:
        return f"{(time.perf_counter() - started) * 1000:.1f}ms"