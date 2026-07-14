"""JSON-RPC-inspired protocol constants and method capabilities."""

PROTOCOL_VERSION = "1.0"

METHOD_CAPABILITIES = {
    "media.recognize_url": "task.propose",
    "media.analyze": "task.propose",
    "media.resolve_formats": "task.propose",
    "task.progress": "task.progress.report",
    "task.error": "task.error.report",
    "ui.describe": "ui.page.describe",
}

