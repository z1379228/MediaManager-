from types import SimpleNamespace

from core.events.event_bus import EventBus
from trusted_ui.optional_workspace_manager import (
    OptionalWorkspaceManager,
    OptionalWorkspaceSpec,
)


class Tabs:
    def __init__(self) -> None:
        self.values: list[object] = []
        self.tooltips: dict[int, str] = {}

    def addTab(self, panel: object, _label: str) -> int:
        self.values.append(panel)
        return len(self.values) - 1

    def setTabToolTip(self, index: int, tooltip: str) -> None:
        self.tooltips[index] = tooltip

    def indexOf(self, panel: object) -> int:
        try:
            return self.values.index(panel)
        except ValueError:
            return -1

    def removeTab(self, index: int) -> None:
        self.values.pop(index)


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
