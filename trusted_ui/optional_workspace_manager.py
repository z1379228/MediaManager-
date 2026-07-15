"""Single lifecycle path for trusted optional workspace tabs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OptionalWorkspaceSpec:
    provider_id: str
    enabled: Callable[[], bool]
    available: Callable[[], bool]
    create: Callable[[], object]
    label: Callable[[object], str]
    tooltip: str


class OptionalWorkspaceManager:
    def __init__(self, tabs: object, specs: tuple[OptionalWorkspaceSpec, ...]) -> None:
        if len({spec.provider_id for spec in specs}) != len(specs):
            raise ValueError("optional workspace IDs are duplicated")
        self.tabs = tabs
        self.specs = {spec.provider_id: spec for spec in specs}
        self.panels: dict[str, object] = {}

    def sync(self, payload: object = None) -> None:
        requested = (
            str(payload.get("provider_id")) if isinstance(payload, dict) else ""
        )
        for provider_id, spec in self.specs.items():
            if requested and requested != provider_id:
                continue
            visible = spec.available() and spec.enabled()
            panel = self.panels.get(provider_id)
            if visible and panel is None:
                panel = spec.create()
                self.panels[provider_id] = panel
                index = self.tabs.addTab(panel, spec.label(panel))
                self.tabs.setTabToolTip(index, spec.tooltip)
            elif not visible and panel is not None:
                self._remove(provider_id, panel)

    def _remove(self, provider_id: str, panel: object) -> None:
        index = self.tabs.indexOf(panel)
        if index >= 0:
            self.tabs.removeTab(index)
        shutdown = getattr(panel, "shutdown", None)
        if callable(shutdown):
            shutdown()
        close = getattr(panel, "close", None)
        if callable(close):
            close()
        delete_later = getattr(panel, "deleteLater", None)
        if callable(delete_later):
            delete_later()
        self.panels.pop(provider_id, None)

    def close_all(self) -> None:
        for provider_id, panel in tuple(self.panels.items()):
            self._remove(provider_id, panel)
