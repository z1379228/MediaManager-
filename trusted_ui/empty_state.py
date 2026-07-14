"""Shared empty-state presentation for trusted workspace panels."""

from __future__ import annotations


def create_empty_state(
    title: str,
    text: str,
    mark: str = "◎",
    parent: object = None,
) -> object:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

    empty = QFrame(parent)
    empty.setObjectName("card")
    layout = QVBoxLayout(empty)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(6)

    mark_label = QLabel(mark)
    mark_label.setObjectName("emptyMark")
    mark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label = QLabel(title)
    title_label.setObjectName("emptyTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_label = QLabel(text)
    text_label.setObjectName("emptyText")
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_label.setWordWrap(True)

    layout.addWidget(mark_label)
    layout.addWidget(title_label)
    layout.addWidget(text_label)
    return empty
