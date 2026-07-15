"""Shared trusted controls for built-in download and discovery MODs."""

from __future__ import annotations

from core.builtin_mod_catalog import builtin_mod_ids
from core.mod_groups import SITE_MOD_CHILDREN, SITE_MOD_PARENT


DOWNLOAD_MOD_IDS = builtin_mod_ids("download")
DISCOVERY_MOD_IDS = builtin_mod_ids("discovery")
FEATURE_MOD_IDS = builtin_mod_ids("feature")


def set_builtin_mod_enabled(
    context: object, provider_id: str, enabled: bool
) -> int:
    """Persist a built-in MOD state and cancel work owned by a disabled MOD."""

    cancelled = 0
    parent_id = SITE_MOD_PARENT.get(provider_id)
    if enabled and parent_id is not None:
        try:
            parent_enabled = context.download_providers.is_enabled(parent_id)
        except (KeyError, RuntimeError) as error:
            raise RuntimeError(f"{parent_id} 主 MOD 不可用") from error
        if not parent_enabled:
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
    if not enabled and provider_id in SITE_MOD_CHILDREN:
        try:
            discovery_statuses = tuple(context.discovery.statuses())
        except (AttributeError, TypeError, RuntimeError):
            discovery_statuses = ()
        available_children = {
            status.provider_id: bool(status.enabled) for status in discovery_statuses
        }
        for child_id in SITE_MOD_CHILDREN[provider_id]:
            if available_children.get(child_id, False):
                context.discovery.set_enabled(child_id, False)
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
