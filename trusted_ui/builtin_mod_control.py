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
    """Persist a MOD state and cancel work owned by a disabled MOD.

    Parent cascades use compensating writes.  If a registry or its compensation
    fails, the caller receives an explicit complete or partial rollback result.
    """

    parent_id = BUILTIN_MOD_PARENT.get(provider_id)
    if enabled and parent_id is not None:
        try:
            parent_available, parent_enabled = _registered_state(context, parent_id)
        except (AttributeError, KeyError, RuntimeError) as error:
            raise RuntimeError(f"{parent_id} 主 MOD 不可用") from error
        if not parent_available or not parent_enabled:
            raise RuntimeError(f"請先啟用 {parent_id} 主 MOD")
    if provider_id not in DOWNLOAD_MOD_IDS | DISCOVERY_MOD_IDS | FEATURE_MOD_IDS:
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
                cascaded_children.append(child_id)

    operations = [(provider_id, enabled), *[(child_id, False) for child_id in cascaded_children]]
    original: dict[str, bool] = {}
    for operation_id, desired in operations:
        available, current = _registered_state(context, operation_id)
        if not available:
            raise KeyError(operation_id)
        original[operation_id] = current

    applied: list[str] = []
    cancelled = 0
    try:
        for operation_id, desired in operations:
            if original[operation_id] == desired:
                continue
            # Registries update their in-memory state before persisting it.
            # Record the attempt first so a save failure also compensates the
            # operation that raised, not only earlier successful calls.
            applied.append(operation_id)
            result = _registry(context, operation_id).set_enabled(operation_id, desired)
            if isinstance(result, int):
                cancelled += result

        if not enabled and provider_id in DOWNLOAD_MOD_IDS:
            affected = tuple(
                task.task_id
                for task in context.download_queue.snapshots()
                if context.download_providers.matching_provider_id(task.request.url)
                == provider_id
            )
            for task_id in affected:
                cancelled += int(context.download_queue.cancel(task_id))
    except Exception as error:
        irreversible_side_effect_unknown = bool(
            getattr(error, "irreversible_side_effect_unknown", False)
        )
        rollback_failures: list[str] = []
        for rollback_id in reversed(applied):
            try:
                _registry(context, rollback_id).set_enabled(
                    rollback_id, original[rollback_id]
                )
            except Exception as rollback_error:
                rollback_failures.append(rollback_id)
                audit = getattr(context, "audit", None)
                if audit is not None:
                    audit.write(
                        "builtin_mod.rollback_failed",
                        provider_id=rollback_id,
                        error_type=type(rollback_error).__name__,
                    )
        try:
            context.builtin_mod_snapshot = None
        except (AttributeError, TypeError):
            pass
        audit = getattr(context, "audit", None)
        if audit is not None:
            audit.write(
                "builtin_mod.enabled_change_failed",
                provider_id=provider_id,
                enabled=enabled,
                affected_children=tuple(cascaded_children),
                changed=tuple(applied),
                error_type=type(error).__name__,
            )
        if cancelled:
            if audit is not None:
                audit.write(
                    "builtin_mod.rollback_irreversible",
                    provider_id=provider_id,
                    cancelled_work=cancelled,
                )
        if irreversible_side_effect_unknown and audit is not None:
            audit.write(
                "builtin_mod.rollback_irreversible_unknown",
                provider_id=provider_id,
                failed_operation=applied[-1] if applied else provider_id,
            )
        if rollback_failures or cancelled or irreversible_side_effect_unknown:
            details: list[str] = []
            if rollback_failures:
                details.append(", ".join(rollback_failures))
            if cancelled:
                details.append(f"已取消 {cancelled} 個工作，無法復原")
            if irreversible_side_effect_unknown:
                details.append("不可逆副作用狀態未知")
            raise RuntimeError(
                f"MOD 狀態切換失敗，回復不完整（{'；'.join(details)}）：{error}"
            ) from error
        raise RuntimeError(f"MOD 狀態切換失敗，已回復：{error}") from error

    try:
        context.builtin_mod_snapshot = None
    except (AttributeError, TypeError):
        pass
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
