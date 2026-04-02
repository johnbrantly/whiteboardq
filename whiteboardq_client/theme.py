"""Light and dark theme definitions and Qt stylesheet generation."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Theme:
    """Color theme definition."""

    name: str
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_card: str           # Card background
    bg_card_hover: str     # Card hover state
    border: str
    border_card: str       # Card borders (slightly lighter)
    text_primary: str
    text_secondary: str
    text_muted: str        # Even more muted text
    accent: str
    accent_blue: str       # Station names
    yellow: str
    yellow_bg: str
    red: str
    red_bg: str
    overdue_bg: str
    success: str
    success_bg: str
    accent_bg: str
    badge_text: str        # Age badge text (high contrast)


DARK_THEME = Theme(
    name="dark",
    bg_primary="#0f0f0f",
    bg_secondary="#1a1a1a",
    bg_tertiary="#252526",
    bg_card="#232323",
    bg_card_hover="#2a2a2a",
    border="#333333",
    border_card="#3a3a3a",
    text_primary="#f0f0f0",
    text_secondary="#888888",
    text_muted="#666666",
    accent="#3b82f6",
    accent_blue="#3b82f6",
    yellow="#eab308",
    yellow_bg="#2a2617",
    red="#ef4444",
    red_bg="#2a1a1a",
    overdue_bg="#3d1f1f",
    success="#22c55e",
    success_bg="#14532d",
    accent_bg="#1e3a5f",
    badge_text="#ffffff",
)

LIGHT_THEME = Theme(
    name="light",
    bg_primary="#f5f5f5",
    bg_secondary="#ffffff",
    bg_tertiary="#e8e8e8",
    bg_card="#ffffff",
    bg_card_hover="#fafafa",
    border="#e0e0e0",
    border_card="#d4d4d4",
    text_primary="#1a1a1a",
    text_secondary="#666666",
    text_muted="#888888",
    accent="#2563eb",
    accent_blue="#2563eb",
    yellow="#ca8a04",
    yellow_bg="#fefce8",
    red="#dc2626",
    red_bg="#fef2f2",
    overdue_bg="#fee2e2",
    success="#16a34a",
    success_bg="#f0fdf4",
    accent_bg="#eff6ff",
    badge_text="#000000",
)

THEMES: Dict[str, Theme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def get_theme(name: str) -> Theme:
    """Get theme by name, defaulting to dark."""
    return THEMES.get(name, DARK_THEME)


def get_stylesheet(theme: Theme) -> str:
    """Generate Qt stylesheet for the given theme."""
    return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {theme.bg_primary};
            color: {theme.text_primary};
        }}

        QLabel {{
            color: {theme.text_primary};
        }}

        QLabel[secondary="true"] {{
            color: {theme.text_secondary};
        }}

        QPushButton {{
            background-color: {theme.bg_card};
            border: 1px solid {theme.border};
            color: {theme.text_primary};
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {theme.bg_card_hover};
            border-color: {theme.border_card};
        }}

        QPushButton:pressed {{
            background-color: {theme.accent};
        }}

        QPushButton:disabled {{
            background-color: {theme.bg_tertiary};
            color: {theme.text_secondary};
            border-color: {theme.bg_tertiary};
            opacity: 0.4;
        }}

        QPushButton[accent="true"] {{
            background-color: {theme.accent};
            border-color: {theme.accent};
            color: white;
        }}

        QPushButton[accent="true"]:hover {{
            background-color: {theme.accent};
        }}

        QPushButton[danger="true"] {{
            background-color: {theme.bg_card};
            border-color: {theme.border};
            color: {theme.text_secondary};
        }}

        QPushButton[danger="true"]:hover {{
            background-color: {theme.red_bg};
            border-color: {theme.red};
            color: {theme.red};
        }}

        QLineEdit {{
            background-color: {theme.bg_secondary};
            border: 1px solid {theme.border};
            color: {theme.text_primary};
            padding: 12px 16px;
            border-radius: 8px;
        }}

        QLineEdit:focus {{
            border-color: {theme.accent};
            border-width: 2px;
        }}

        QTextEdit {{
            background-color: {theme.bg_primary};
            border: 1px solid {theme.border};
            color: {theme.text_primary};
            border-radius: 4px;
        }}

        QScrollArea {{
            background-color: {theme.bg_primary};
            border: none;
        }}

        QScrollBar:vertical {{
            background-color: {theme.bg_primary};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {theme.border};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {theme.text_secondary};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QCheckBox {{
            color: {theme.text_primary};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.border};
            border-radius: 3px;
            background-color: {theme.bg_primary};
        }}

        QCheckBox::indicator:checked {{
            background-color: {theme.accent};
            border-color: {theme.accent};
        }}

        QComboBox {{
            background-color: {theme.bg_secondary};
            border: 1px solid {theme.border};
            color: {theme.text_primary};
            padding: 8px;
            border-radius: 4px;
        }}

        QComboBox:hover {{
            border-color: {theme.accent};
        }}

        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {theme.bg_secondary};
            color: {theme.text_primary};
            selection-background-color: {theme.accent};
            border: 1px solid {theme.border};
        }}

        QGroupBox {{
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 8px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}

        QMenuBar {{
            background-color: {theme.bg_secondary};
            color: {theme.text_primary};
            border-bottom: 1px solid {theme.border};
        }}

        QMenuBar::item {{
            padding: 4px 8px;
        }}

        QMenuBar::item:selected {{
            background-color: {theme.accent};
        }}

        QMenu {{
            background-color: {theme.bg_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
        }}

        QMenu::item {{
            padding: 6px 20px;
        }}

        QMenu::item:selected {{
            background-color: {theme.accent};
        }}
    """
