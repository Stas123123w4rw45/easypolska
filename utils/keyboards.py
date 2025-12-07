"""Keyboard layouts for bot interactions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Survival Mode", callback_data="survival_mode")],
        [InlineKeyboardButton(text="📚 Review Words", callback_data="review_words")],
        [InlineKeyboardButton(text="📊 My Progress", callback_data="my_progress")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    return keyboard


def get_scenario_selection_keyboard(scenarios: List[dict]) -> InlineKeyboardMarkup:
    """Get scenario selection keyboard."""
    buttons = []
    for scenario in scenarios:
        level_emoji = {"A1": "🟢", "A2": "🟡", "B1": "🟠"}.get(scenario["level"], "⚪")
        buttons.append([
            InlineKeyboardButton(
                text=f"{level_emoji} {scenario['title']}",
                callback_data=f"scenario_{scenario['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_keyboard(options: List[str], question_id: str = "quiz") -> InlineKeyboardMarkup:
    """Get quiz answer keyboard."""
    buttons = []
    for i, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"{question_id}_{i}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_continue_keyboard(next_action: str = "continue") -> InlineKeyboardMarkup:
    """Get continue/next keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Continue", callback_data=next_action)],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
    ])
    return keyboard


def get_review_start_keyboard(due_count: int) -> InlineKeyboardMarkup:
    """Get keyboard to start review session."""
    if due_count == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"▶️ Start Review ({due_count} words)", callback_data="start_review")],
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
        ])
    return keyboard


def get_settings_keyboard(current_level: str) -> InlineKeyboardMarkup:
    """Get settings keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📊 Current Level: {current_level}", callback_data="change_level")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
    ])
    return keyboard


def get_level_selection_keyboard() -> InlineKeyboardMarkup:
    """Get level selection keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 (Beginner)", callback_data="level_A1")],
        [InlineKeyboardButton(text="🟡 A2 (Elementary)", callback_data="level_A2")],
        [InlineKeyboardButton(text="🟠 B1 (Intermediate)", callback_data="level_B1")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="settings")]
    ])
    return keyboard
