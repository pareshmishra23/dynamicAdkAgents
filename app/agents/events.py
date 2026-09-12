from __future__ import annotations

import queue
import threading
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterator


@dataclass(frozen=True)
class AgentEvent:
    kind: str
    run_id: str
    agent_id: str | None = None
    detail: str = ""


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[AgentEvent], None]] = []
        self._history: list[AgentEvent] = []

    def subscribe(self, subscriber: Callable[[AgentEvent], None]) -> None:
        self._subscribers.append(subscriber)

    def emit(self, event: AgentEvent) -> None:
        self._history.append(event)
        for subscriber in list(self._subscribers):
            subscriber(event)

    def history(self, kind: str | None = None) -> tuple[AgentEvent, ...]:
        if kind is None:
            return tuple(self._history)
        return tuple(event for event in self._history if event.kind == kind)


class ApprovalEventBus(EventBus):
    def pending(self, run_id: str, agent_id: str, detail: str = "") -> None:
        self.emit(AgentEvent(kind="approval_pending", run_id=run_id, agent_id=agent_id, detail=detail))

    def approved(self, run_id: str, agent_id: str) -> None:
        self.emit(AgentEvent(kind="approval_approved", run_id=run_id, agent_id=agent_id))

    def rejected(self, run_id: str, agent_id: str) -> None:
        self.emit(AgentEvent(kind="approval_rejected", run_id=run_id, agent_id=agent_id))


class EventStream:
    def __init__(self) -> None:
        self._queue: queue.Queue[AgentEvent | None] = queue.Queue()
        self._open = True

    def record(self, event: AgentEvent) -> None:
        if self._open:
            self._queue.put(event)

    def events(self) -> Iterator[AgentEvent]:
        while self._open:
            event = self._queue.get()
            if event is None:
                break
            yield event

    def close(self) -> None:
        self._open = False
        self._queue.put(None)


class WebhookSink:
    def __init__(self, url: str, timeout: float = 5.0) -> None:
        self.url = url
        self.timeout = timeout
        self._lock = threading.Lock()

    def record(self, event: AgentEvent) -> None:
        import json

        body = (
            '{"kind": "%s", "run_id": "%s", "agent_id": "%s", "detail": "%s"}'
            % (
                event.kind,
                event.run_id,
                event.agent_id or "",
                event.detail.replace('"', "'"),
            )
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=body, method="POST", headers={"Content-Type": "application/json"}
        )
        with self._lock:
            urllib.request.urlopen(request, timeout=self.timeout)