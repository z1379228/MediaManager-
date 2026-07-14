"""Shared trusted controls for built-in download and discovery MODs."""

from __future__ import annotations


DOWNLOAD_MOD_IDS = frozenset({"youtube", "generic-ytdlp", "bilibili"})
DISCOVERY_MOD_IDS = frozenset(
    {
        "youtube-search",
        "youtube-player",
        "youtube-history",
        "youtube-recovery",
        "youtube-similar",
        "youtube-auto-split",
    }
)
FEATURE_MOD_IDS = frozenset({"automation", "media-convert", "speech-to-text"})


def set_builtin_mod_enabled(
    context: object, provider_id: str, enabled: bool
) -> int:
    """Persist a built-in MOD state and cancel work owned by a disabled MOD."""

    cancelled = 0
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
        events.publish(
            "builtin_mod.changed",
            {
                "provider_id": provider_id,
                "enabled": enabled,
                "cancelled_tasks": cancelled,
            },
        )
    return cancelled
