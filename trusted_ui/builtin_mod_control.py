"""Shared trusted controls for built-in download and discovery MODs."""

from __future__ import annotations

from core.builtin_mod_catalog import (
    BUILTIN_MOD_CHILDREN,
    BUILTIN_MOD_PARENT,
    builtin_mod_descriptor,
    builtin_mod_ids,
)


DOWNLOAD_MOD_IDS = builtin_mod_ids("download")
DISCOVERY_MOD_IDS = builtin_mod_ids("discovery")
FEATURE_MOD_IDS = builtin_mod_ids("feature")


def _registry(context: object, provider_id: str) -> object:
    kind = builtin_mod_descriptor(provider_id).kind
    if kind == "download":
        return context.download_providers
    if kind == "discovery":
        return context.discovery
    if kind == "feature":
        return context.features
    raise KeyError(provider_id)


def _registered_state(context: object, provider_id: str) -> tuple[bool, bool]:
    registry = _registry(context, provider_id)
    raw_statuses = registry.statuses()
    if not isinstance(raw_statuses, (list, tuple)):
        return False, False
    statuses = {
        status.provider_id: status for status in raw_statuses
    }
    status = statuses.get(provider_id)
    return status is not None, bool(status.enabled) if status is not None else False


def builtin_mod_is_enabled(context: object, provider_id: str) -> bool:
    """Return one built-in MOD state regardless of its backing registry."""

    available, enabled = _registered_state(context, provider_id)
    return available and enabled


def set_builtin_mod_enabled(
    context: object, provider_id: str, enabled: bool
) -> int:
    """Persist a built-in MOD state and cancel work owned by a disabled MOD."""

    cancelled = 0
    parent_id = BUILTIN_MOD_PARENT.get(provider_id)
    if enabled and parent_id is not None:
        try:
            parent_available, parent_enabled = _registered_state(context, parent_id)
        except (AttributeError, KeyError, RuntimeError) as error:
            raise RuntimeError(f"{parent_id} 主 MOD 不可用") from error
        if not parent_available or not parent_enabled:
            raise RuntimeError(f"請先啟用 {parent_id} 主 MOD")
    if provider_id in DOWNLOAD_MOD_IDS:
        available = {
            status.provider_id for status in context.download_providers.statuses()
        }
        if provider_id not in available:
            raise KeyError(provider_id)
        affected = ()
        if not enabled:
            affected = tuple(
                task.task_id
                for task in context.download_queue.snapshots()
                if context.download_providers.matching_provider_id(task.request.url)
                == provider_id
            )
        context.download_providers.set_enabled(provider_id, enabled)
        for task_id in affected:
            cancelled += int(context.download_queue.cancel(task_id))
    elif provider_id in DISCOVERY_MOD_IDS:
        available = {status.provider_id for status in context.discovery.statuses()}
        if provider_id not in available:
            raise KeyError(provider_id)
        context.discovery.set_enabled(provider_id, enabled)
    elif provider_id in FEATURE_MOD_IDS:
        available = {status.provider_id for status in context.features.statuses()}
        if provider_id not in available:
            raise KeyError(provider_id)
        cancelled = context.features.set_enabled(provider_id, enabled)
    else:
        raise KeyError(provider_id)

    cascaded_children: list[str] = []
    if not enabled and provider_id in BUILTIN_MOD_CHILDREN:
        for child_id in BUILTIN_MOD_CHILDREN[provider_id]:
            try:
                available, child_enabled = _registered_state(context, child_id)
            except (AttributeError, KeyError, RuntimeError):
                available = False
                child_enabled = False
            if available and child_enabled:
                child_cancelled = _registry(context, child_id).set_enabled(
                    child_id, False
                )
                if isinstance(child_cancelled, int):
                    cancelled += child_cancelled
                cascaded_children.append(child_id)

    audit = getattr(context, "audit", None)
    if audit is not None:
        audit.write(
            "builtin_mod.enabled_changed",
            provider_id=provider_id,
            enabled=enabled,
            cancelled_tasks=cancelled,
        )
    events = getattr(context, "events", None)
    if events is not None:
        for child_id in cascaded_children:
            events.publish(
                "builtin_mod.changed",
                {
                    "provider_id": child_id,
                    "enabled": False,
                    "cancelled_tasks": 0,
                },
            )
        events.publish(
            "builtin_mod.changed",
            {
                "provider_id": provider_id,
                "enabled": enabled,
                "cancelled_tasks": cancelled,
            },
        )
    return cancelled
