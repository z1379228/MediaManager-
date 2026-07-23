"""Central visual tokens and stylesheet for the trusted desktop UI."""

from __future__ import annotations


COLORS = {
    "success": "#35c98f",
    "warning": "#f3b95f",
    "danger": "#ff6b7a",
    "info": "#75a7ff",
    "muted": "#8f9bb3",
}

UI_SCALE_VALUES = ("compact", "standard", "large")


def apply_application_theme(application: object, ui_scale: object = "standard") -> None:
    """Apply both palette and QSS so Qt popup/viewport surfaces stay dark."""

    from PySide6.QtGui import QColor, QPalette

    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#0a0f1d",
        QPalette.ColorRole.WindowText: "#e9eef8",
        QPalette.ColorRole.Base: "#080f1c",
        QPalette.ColorRole.AlternateBase: "#0f192b",
        QPalette.ColorRole.ToolTipBase: "#172239",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.Text: "#e9eef8",
        QPalette.ColorRole.Button: "#1b2740",
        QPalette.ColorRole.ButtonText: "#e9eef8",
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Highlight: "#4f6fd8",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: "#66728a",
    }
    for role, value in colors.items():
        palette.setColor(role, QColor(value))
    application.setStyle("Fusion")
    application.setPalette(palette)
    application.setStyleSheet(application_stylesheet(ui_scale))


def normalized_ui_scale(value: object) -> str:
    return value if isinstance(value, str) and value in UI_SCALE_VALUES else "standard"


def ui_scale_stylesheet(value: object) -> str:
    scale = normalized_ui_scale(value)
    if scale == "compact":
        return r"""
QWidget { font-size: 13px; }
QLabel#title { font-size: 23px; }
QLabel#sectionTitle { font-size: 18px; }
QLabel#sectionSubtitle, QLabel#emptyText { font-size: 12px; }
QLabel#taskDetailText, QLabel#fieldLabel { font-size: 11px; }
QLabel#statValue { font-size: 20px; }
QLabel#badge, QLabel#providerBadge { font-size: 11px; padding: 3px 8px; }
QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox { padding: 6px 9px; }
QPushButton { padding: 7px 11px; }
QTableWidget::item { padding: 6px; }
QHeaderView::section { padding: 7px; font-size: 11px; }
QTabBar::tab { padding: 8px 15px; }
QMenu::item { padding: 7px 20px 7px 11px; }
"""
    if scale == "large":
        return r"""
QWidget { font-size: 15px; }
QLabel#title { font-size: 26px; }
QLabel#sectionTitle { font-size: 21px; }
QLabel#sectionSubtitle, QLabel#emptyText { font-size: 15px; }
QLabel#taskDetailText, QLabel#fieldLabel { font-size: 14px; }
QLabel#emptyTitle { font-size: 19px; }
QLabel#statValue { font-size: 23px; }
QLabel#badge, QLabel#providerBadge { font-size: 13px; }
QHeaderView::section { font-size: 14px; }
"""
    return ""


def application_stylesheet(ui_scale: object = "standard") -> str:
    base = r"""
QMainWindow, QDialog { background: #0a0f1d; }
QWidget {
    color: #e9eef8;
    font-family: "Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI Variable", "Segoe UI";
    font-size: 14px;
}
QWidget#appRoot { background: transparent; }
QScrollArea#workspaceScroll,
QScrollArea#workspaceScroll > QWidget,
QScrollArea#workspaceScroll > QWidget > QWidget {
    background: transparent;
    border: none;
}
QLabel, QCheckBox { background: transparent; }
QFrame#topBar, QFrame#card, QFrame#statCard {
    background: rgba(15, 23, 40, 220);
    border: 1px solid rgba(92, 113, 155, 82);
    border-radius: 12px;
}
QFrame#topBar {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 rgba(14, 26, 49, 238),
        stop: 0.55 rgba(19, 28, 48, 232),
        stop: 1 rgba(29, 24, 52, 232)
    );
    border-color: rgba(111, 141, 255, 92);
}
QFrame#card { background: rgba(13, 21, 37, 218); }
QFrame#footerBar { background: transparent; border: none; }
QFrame#downloadNotice {
    background: #133b32;
    border: 1px solid #246653;
    border-radius: 10px;
}
QFrame#taskDetailCard {
    background: rgba(12, 20, 35, 228);
    border: 1px solid rgba(73, 92, 128, 148);
    border-radius: 9px;
}
QLabel#taskDetailText { color: #b8c5dc; font-size: 13px; }
QLabel#taskDetailText[taskState="failed"] { color: #ff9aa4; }
QLabel#taskDetailText[taskState="completed"] { color: #79e0b7; }
QLabel#downloadNoticeText { color: #9aebc9; font-weight: 700; }
QFrame#statCard { background: rgba(15, 23, 40, 232); }
QLabel#appMark {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #7291ff, stop: 1 #765ee8
    );
    color: white;
    border-radius: 10px;
    font-size: 19px;
    font-weight: 800;
    padding: 8px 11px;
}
QLabel#title { color: #ffffff; font-size: 25px; font-weight: 750; }
QLabel#subtitle, QLabel#muted, QLabel#statLabel { color: #8f9bb3; }
QLabel#sectionTitle { color: #ffffff; font-size: 20px; font-weight: 700; }
QLabel#sectionSubtitle { color: #8f9bb3; font-size: 14px; }
QLabel#emptyMark { color: #536585; font-size: 42px; }
QLabel#emptyTitle { color: #ffffff; font-size: 18px; font-weight: 700; }
QLabel#emptyText { color: #8f9bb3; font-size: 14px; }
QLabel#fieldLabel { color: #b8c2d7; font-size: 13px; font-weight: 650; }
QLabel#statValue { color: #ffffff; font-size: 22px; font-weight: 750; }
QLabel#preview { color: #c8d5ed; padding: 8px 2px; }
QLabel#badge, QLabel#providerBadge {
    background: #1c2b49;
    color: #9dbaff;
    border: 1px solid #304771;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 12px;
    font-weight: 700;
}
QLabel#badge[securityState="normal"] {
    background: #133b32; color: #79e0b7; border-color: #246653;
}
QLabel#badge[securityState="safe"] {
    background: #3a2b17; color: #ffd38a; border-color: #6d5128;
}
QLabel#badge[securityState="blocked"] {
    background: #3b1d29; color: #ff9aa4; border-color: #71384b;
}
QLabel#badge[securityState="unknown"] {
    background: #282d3a; color: #b8c2d7; border-color: #454d60;
}
QLabel#providerBadge[active="true"] {
    background: #133b32;
    color: #79e0b7;
    border-color: #246653;
}
QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox {
    background: rgba(8, 15, 28, 226);
    border: 1px solid rgba(73, 92, 128, 184);
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #4f6fd8;
}
QAbstractScrollArea,
QAbstractScrollArea QWidget#qt_scrollarea_viewport,
QScrollArea,
QListView,
QTreeView,
QTableView,
QComboBox QAbstractItemView {
    background: #080f1c;
    alternate-background-color: #0f192b;
    color: #e9eef8;
    border: 1px solid #2f3d59;
    selection-background-color: #203866;
    selection-color: #ffffff;
    outline: none;
}
QComboBox QAbstractItemView::item { min-height: 30px; padding: 4px 8px; }
QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {
    background: #080f1c;
    color: #e9eef8;
    border: 1px solid #495c80;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #4f6fd8;
}
QMessageBox, QFileDialog { background: #0a0f1d; color: #e9eef8; }
QLineEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus, QComboBox:focus { border-color: #6f8dff; }
QTreeView:focus, QTreeWidget:focus {
    border: 2px solid #6f8dff;
}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextBrowser:disabled { color: #66728a; background: #0b111e; }
QComboBox::drop-down { border: none; width: 24px; }
QPushButton {
    background: #1b2740;
    border: 1px solid #33425f;
    border-radius: 8px;
    padding: 8px 13px;
    min-height: 20px;
    font-weight: 650;
}
QPushButton:hover { background: #243452; border-color: #465a80; }
QPushButton:pressed { background: #18233a; }
QPushButton:disabled { color: #667085; background: #111827; border-color: #253049; }
QPushButton#primary {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #5f7df7, stop: 1 #765ee8
    );
    border-color: #8299ff;
    color: white;
}
QPushButton#primary:hover { background: #718cff; }
QPushButton#danger { color: #ff9aa4; border-color: #643746; background: #2a1924; }
QPushButton#ghost { background: transparent; }
QPushButton#environment {
    background: #1b2740;
    color: #c8d5ed;
    padding: 6px 10px;
}
QPushButton#environment[dependencyState="ready"] {
    background: #133b32; color: #79e0b7; border-color: #246653;
}
QPushButton#environment[dependencyState="warning"] {
    background: #3a2b17; color: #ffd38a; border-color: #6d5128;
}
QLabel#dependencySummary {
    background: #182238;
    border: 1px solid #2b3854;
    border-radius: 8px;
    padding: 9px 12px;
}
QLabel#dependencySummary[dependencyState="ready"] {
    background: #133b32; color: #79e0b7; border-color: #246653;
}
QLabel#dependencySummary[dependencyState="warning"] {
    background: #3a2b17; color: #ffd38a; border-color: #6d5128;
}
QPushButton:focus, QComboBox:focus, QPlainTextEdit:focus, QTextBrowser:focus, QTableWidget:focus {
    border-color: #6f8dff;
}
QCheckBox { spacing: 8px; color: #c8d2e5; }
QCheckBox::indicator { width: 18px; height: 18px; }
QTableWidget {
    background: rgba(8, 15, 28, 218);
    alternate-background-color: rgba(15, 25, 43, 224);
    border: 1px solid rgba(73, 92, 128, 148);
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: #203866;
    selection-color: white;
}
QTableWidget::item { padding: 8px; border-bottom: 1px solid #1d2940; }
QHeaderView::section {
    background: #131d30;
    color: #9eabc2;
    border: none;
    border-bottom: 1px solid #2a3650;
    padding: 9px;
    font-size: 13px;
    font-weight: 700;
}
QProgressBar {
    background: #182238;
    border: none;
    border-radius: 5px;
    color: #dfe8fb;
    height: 10px;
    text-align: center;
    font-size: 11px;
}
QProgressBar::chunk { background: #6584ff; border-radius: 5px; }
QTabWidget::pane { border: none; margin-top: 8px; }
QTabWidget#workspaceTabs, QTabWidget#workspaceTabs > QTabBar {
    background: transparent;
    border: none;
}
QTabBar::tab {
    background: transparent;
    color: #8f9bb3;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 18px;
    margin-right: 4px;
    font-weight: 650;
}
QTabBar::tab:hover { color: #cbd6ea; background: #111a2c; }
QTabBar::tab:selected {
    color: #ffffff;
    background: #151f34;
    border-bottom-color: #6f8dff;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #32415f; border-radius: 5px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #32415f; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu {
    background: #151f34;
    border: 1px solid #33425f;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item { padding: 8px 22px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background: #243452; color: white; }
QToolTip { background: #172239; color: white; border: 1px solid #405173; padding: 5px; }
"""
    return base + ui_scale_stylesheet(ui_scale)
