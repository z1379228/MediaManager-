from types import SimpleNamespace
from unittest.mock import Mock

from core.events.event_bus import EventBus
from trusted_ui.optional_workspace_manager import (
    OptionalWorkspaceManager,
    OptionalWorkspaceSpec,
)


class Tabs:
    def __init__(self) -> None:
        self.values: list[object] = []
        self.tooltips: dict[int, str] = {}
        self.current_index = -1

    def addTab(self, panel: object, _label: str) -> int:
        self.values.append(panel)
        if self.current_index < 0:
            self.current_index = 0
        return len(self.values) - 1

    def insertTab(self, index: int, panel: object, _label: str) -> int:
        self.values.insert(index, panel)
        return index

    def setTabToolTip(self, index: int, tooltip: str) -> None:
        self.tooltips[index] = tooltip

    def indexOf(self, panel: object) -> int:
        try:
            return self.values.index(panel)
        except ValueError:
            return -1

    def removeTab(self, index: int) -> None:
        self.values.pop(index)
        if not self.values:
            self.current_index = -1
        elif self.current_index >= len(self.values):
            self.current_index = len(self.values) - 1

    def currentWidget(self) -> object | None:
        if self.current_index < 0:
            return None
        return self.values[self.current_index]

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = index

    def widget(self, index: int) -> object:
        return self.values[index]


def test_optional_workspace_has_one_create_and_cleanup_path() -> None:
    enabled = {"one": False}
    created: list[object] = []

    def create() -> object:
        panel = SimpleNamespace(
            shutdown_calls=0,
            close_calls=0,
            delete_calls=0,
        )
        panel.shutdown = lambda: setattr(
            panel, "shutdown_calls", panel.shutdown_calls + 1
        )
        panel.close = lambda: setattr(panel, "close_calls", panel.close_calls + 1)
        panel.deleteLater = lambda: setattr(
            panel, "delete_calls", panel.delete_calls + 1
        )
        created.append(panel)
        return panel

    tabs = Tabs()
    manager = OptionalWorkspaceManager(
        tabs,
        (
            OptionalWorkspaceSpec(
                "one",
                lambda: enabled["one"],
                lambda: True,
                create,
                lambda _panel: "One",
                "tooltip",
            ),
        ),
    )

    manager.sync()
    assert not created
    enabled["one"] = True
    manager.sync({"provider_id": "one"})
    manager.sync({"provider_id": "one"})
    assert len(created) == 1
    assert len(tabs.values) == 1

    panel = created[0]
    enabled["one"] = False
    manager.sync({"provider_id": "one"})
    assert manager.panels == {}
    assert panel.shutdown_calls == 1
    assert panel.close_calls == 1
    assert panel.delete_calls == 1


def test_event_bus_unsubscribe_prevents_stale_optional_callbacks() -> None:
    events = EventBus()
    received: list[object] = []

    def handler(payload: object) -> None:
        received.append(payload)

    events.subscribe("changed", handler)
    events.subscribe("changed", handler)
    events.publish("changed", 1)
    events.unsubscribe("changed", handler)
    events.publish("changed", 2)

    assert received == [1]


def test_optional_workspace_can_defer_panel_until_selected() -> None:
    enabled = {"one": True}
    created: list[object] = []
    placeholders: list[object] = []

    def create_panel() -> object:
        panel = SimpleNamespace(
            shutdown_calls=0,
            close_calls=0,
            delete_calls=0,
        )
        panel.shutdown = lambda: setattr(
            panel, "shutdown_calls", panel.shutdown_calls + 1
        )
        panel.close = lambda: setattr(panel, "close_calls", panel.close_calls + 1)
        panel.deleteLater = lambda: setattr(
            panel, "delete_calls", panel.delete_calls + 1
        )
        created.append(panel)
        return panel

    def create_placeholder(_provider_id: str, _label: str) -> object:
        placeholder = SimpleNamespace(close=Mock(), deleteLater=Mock())
        placeholders.append(placeholder)
        return placeholder

    tabs = Tabs()
    manager = OptionalWorkspaceManager(
        tabs,
        (
            OptionalWorkspaceSpec(
                "one",
                lambda: enabled["one"],
                lambda: True,
                create_panel,
                lambda _panel: "One ready",
                "tooltip",
                "One",
            ),
        ),
        placeholder_factory=create_placeholder,
    )

    manager.sync()
    assert not created
    assert tabs.values == placeholders

    panel = manager.ensure_current(0)

    assert panel is created[0]
    assert tabs.values == [panel]
    assert manager.panels == {"one": panel}
    assert manager.placeholders == {}
    placeholders[0].close.assert_called_once_with()
    placeholders[0].deleteLater.assert_called_once_with()

    assert manager.ensure("one") is panel
    assert len(created) == 1

    enabled["one"] = False
    manager.sync({"provider_id": "one"})
    assert panel.shutdown_calls == 1
