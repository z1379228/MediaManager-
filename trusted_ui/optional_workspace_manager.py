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
    placeholder_label: str = ""


class OptionalWorkspaceManager:
    def __init__(
        self,
        tabs: object,
        specs: tuple[OptionalWorkspaceSpec, ...],
        *,
        placeholder_factory: Callable[[str, str], object] | None = None,
    ) -> None:
        if len({spec.provider_id for spec in specs}) != len(specs):
            raise ValueError("optional workspace IDs are duplicated")
        self.tabs = tabs
        self.specs = {spec.provider_id: spec for spec in specs}
        self.placeholder_factory = placeholder_factory
        self.panels: dict[str, object] = {}
        self.placeholders: dict[str, object] = {}
        self._materializing = False

    def sync(self, payload: object = None) -> None:
        requested = (
            str(payload.get("provider_id")) if isinstance(payload, dict) else ""
        )
        for provider_id, spec in self.specs.items():
            if requested and requested != provider_id:
                continue
            visible = spec.available() and spec.enabled()
            item = self.panels.get(provider_id) or self.placeholders.get(provider_id)
            if visible and item is None:
                if self.placeholder_factory is None:
                    panel = spec.create()
                    self.panels[provider_id] = panel
                    index = self.tabs.addTab(panel, spec.label(panel))
                else:
                    label = spec.placeholder_label or provider_id
                    placeholder = self.placeholder_factory(provider_id, label)
                    self.placeholders[provider_id] = placeholder
                    index = self.tabs.addTab(placeholder, label)
                self.tabs.setTabToolTip(index, spec.tooltip)
            elif not visible and item is not None:
                self._remove(provider_id, item)

    def ensure(self, provider_id: str) -> object | None:
        panel = self.panels.get(provider_id)
        if panel is not None:
            return panel
        spec = self.specs.get(provider_id)
        if spec is None or not (spec.available() and spec.enabled()):
            return None
        placeholder = self.placeholders.get(provider_id)
        if placeholder is None:
            self.sync({"provider_id": provider_id})
            placeholder = self.placeholders.get(provider_id)
            panel = self.panels.get(provider_id)
            if panel is not None or placeholder is None:
                return panel
        index = self.tabs.indexOf(placeholder)
        if index < 0:
            return None
        current_widget = getattr(self.tabs, "currentWidget", None)
        was_current = callable(current_widget) and current_widget() is placeholder
        self._materializing = True
        try:
            panel = spec.create()
            self.tabs.removeTab(index)
            self.placeholders.pop(provider_id, None)
            self.panels[provider_id] = panel
            inserted = self.tabs.insertTab(index, panel, spec.label(panel))
            self.tabs.setTabToolTip(inserted, spec.tooltip)
            if was_current:
                set_current = getattr(self.tabs, "setCurrentIndex", None)
                if callable(set_current):
                    set_current(inserted)
            self._dispose(placeholder, shutdown=False)
            return panel
        finally:
            self._materializing = False

    def ensure_current(self, index: int) -> object | None:
        if self._materializing or index < 0:
            return None
        widget_at = getattr(self.tabs, "widget", None)
        if not callable(widget_at):
            return None
        selected = widget_at(index)
        for provider_id, placeholder in tuple(self.placeholders.items()):
            if selected is placeholder:
                return self.ensure(provider_id)
        return None

    def _remove(self, provider_id: str, panel: object) -> None:
        index = self.tabs.indexOf(panel)
        if index >= 0:
            self.tabs.removeTab(index)
        self._dispose(
            panel,
            shutdown=provider_id in self.panels,
        )
        self.panels.pop(provider_id, None)
        self.placeholders.pop(provider_id, None)

    @staticmethod
    def _dispose(panel: object, *, shutdown: bool) -> None:
        stop = getattr(panel, "shutdown", None)
        if shutdown and callable(stop):
            stop()
        close = getattr(panel, "close", None)
        if callable(close):
            close()
        delete_later = getattr(panel, "deleteLater", None)
        if callable(delete_later):
            delete_later()

    def close_all(self) -> None:
        self._materializing = True
        try:
            for provider_id, panel in tuple(self.panels.items()):
                self._remove(provider_id, panel)
            for provider_id, placeholder in tuple(self.placeholders.items()):
                self._remove(provider_id, placeholder)
        finally:
            self._materializing = False
