"""Keyboard layouts for bot interactions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Вивчати Слова", callback_data="flashcard_learning")],
        [InlineKeyboardButton(text="📝 Тренування", callback_data="fill_blank_training")],
        [InlineKeyboardButton(text="📖 Словник", callback_data="vocabulary_browser")],
        [InlineKeyboardButton(text="🎯 Виживання", callback_data="survival_mode")],
        [InlineKeyboardButton(text="📊 Прогрес", callback_data="my_progress")],
        [InlineKeyboardButton(text="⚙️ Налаштування", callback_data="settings")]
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
    buttons.append([InlineKeyboardButton(text="🔙 Назад до Меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_keyboard(options: List[str], question_id: str = "quiz", show_cancel: bool = False) -> InlineKeyboardMarkup:
    """Get quiz answer keyboard."""
    buttons = []
    for i, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"{question_id}_{i}"
            )
        ])
    
    if show_cancel:
        buttons.append([InlineKeyboardButton(text="🚫 Скасувати", callback_data=f"{question_id}_cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_continue_keyboard(next_action: str = "continue") -> InlineKeyboardMarkup:
    """Get continue/next keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️", callback_data=next_action)]
    ])
    return keyboard


def get_review_start_keyboard(due_count: int) -> InlineKeyboardMarkup:
    """Get keyboard to start review session."""
    if due_count == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"▶️ Почати Повторення ({due_count} слів)", callback_data="start_review")],
            [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
        ])
    return keyboard


def get_settings_keyboard(current_level: str) -> InlineKeyboardMarkup:
    """Get settings keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📊 Поточний Рівень: {current_level}", callback_data="change_level")],
        [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
    ])
    return keyboard


def get_level_selection_keyboard() -> InlineKeyboardMarkup:
    """Get level selection keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 (Початковий)", callback_data="level_A1")],
        [InlineKeyboardButton(text="🟡 A2 (Елементарний)", callback_data="level_A2")],
        [InlineKeyboardButton(text="🟠 B1 (Середній)", callback_data="level_B1")],
        [InlineKeyboardButton(text="🔙", callback_data="settings")]
    ])
    return keyboard


def get_vocabulary_browser_keyboard(page: int = 0, total_pages: int = 1, filter_type: str = "all") -> InlineKeyboardMarkup:
    """Get vocabulary browser keyboard with filters and pagination."""
    buttons = []
    
    # Filter buttons
    filter_row = []
    filters = [
        ("📚 Всі", "vocab_filter_all"),
        ("✅ Знаю", "vocab_filter_known"),
        ("📖 Вивчаю", "vocab_filter_learning"),
        ("🆕 Нові", "vocab_filter_new")
    ]
    for text, data in filters:
        marker = "• " if filter_type in data else ""
        filter_row.append(InlineKeyboardButton(text=f"{marker}{text}", callback_data=data))
    
    buttons.append(filter_row[:2])
    buttons.append(filter_row[2:])
    
    # Pagination
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"vocab_page_{page-1}"))
        nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="vocab_noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"vocab_page_{page+1}"))
        buttons.append(nav_row)
    
    # Actions
    buttons.append([InlineKeyboardButton(text="➕ Додати слово", callback_data="vocab_add_word")])
    buttons.append([InlineKeyboardButton(text="🏠", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_word_detail_keyboard(word_id: int, in_learning: bool = False) -> InlineKeyboardMarkup:
    """Get keyboard for word details view."""
    buttons = []
    
    if in_learning:
        buttons.append([InlineKeyboardButton(text="🗑️ Видалити зі списку", callback_data=f"vocab_remove_{word_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ Додати до вивчення", callback_data=f"vocab_add_{word_id}")])
    
    buttons.append([InlineKeyboardButton(text="🔙", callback_data="vocabulary_browser")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_session_complete_keyboard(errors_count: int = 0) -> InlineKeyboardMarkup:
    """Get keyboard for session completion with option to review errors."""
    buttons = []
    
    if errors_count > 0:
        buttons.append([InlineKeyboardButton(text=f"🔄 Повторити помилки ({errors_count})", callback_data="review_errors")])
    
    buttons.append([InlineKeyboardButton(text="➕ Вивчити нові", callback_data="flashcard_learning")])
    buttons.append([InlineKeyboardButton(text="🏠", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_flashcard_word_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for showing word in flashcard mode."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀", callback_data="show_translation")]
    ])
    return keyboard


def get_flashcard_feedback_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for flashcard feedback (know/don't know)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅", callback_data="flashcard_know"),
         InlineKeyboardButton(text="❌", callback_data="flashcard_dont_know")],
        [InlineKeyboardButton(text="🗑️", callback_data="flashcard_delete")]
    ])
    return keyboard


def get_bottom_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get persistent bottom menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠"), KeyboardButton(text="📚"), KeyboardButton(text="📝"), KeyboardButton(text="📊")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard
