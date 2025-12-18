"""Handlers for vocabulary browser and word management."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from math import ceil

from models import models
from models.models import User, Vocabulary, WordLearningStats
from utils.states import MainMenu
from utils.keyboards import (
    get_vocabulary_browser_keyboard,
    get_word_detail_keyboard,
    get_main_menu_keyboard
)

router = Router()

WORDS_PER_PAGE = 10


@router.callback_query(F.data == "vocabulary_browser")
async def show_vocabulary_browser(callback: CallbackQuery, state: FSMContext):
    """Show vocabulary browser with all words."""
    await state.update_data(vocab_page=0, vocab_filter="all")
    await display_vocabulary_page(callback, state, page=0, filter_type="all")


@router.callback_query(F.data.startswith("vocab_filter_"))
async def filter_vocabulary(callback: CallbackQuery, state: FSMContext):
    """Filter vocabulary by type."""
    filter_type = callback.data.replace("vocab_filter_", "")
    await state.update_data(vocab_filter=filter_type, vocab_page=0)
    await display_vocabulary_page(callback, state, page=0, filter_type=filter_type)


@router.callback_query(F.data.startswith("vocab_page_"))
async def change_vocabulary_page(callback: CallbackQuery, state: FSMContext):
    """Change vocabulary page."""
    page = int(callback.data.replace("vocab_page_", ""))
    data = await state.get_data()
    filter_type = data.get("vocab_filter", "all")
    await display_vocabulary_page(callback, state, page=page, filter_type=filter_type)


async def display_vocabulary_page(callback: CallbackQuery, state: FSMContext, page: int = 0, filter_type: str = "all"):
    """Display vocabulary page with words."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Get all vocabulary
        vocab_query = select(Vocabulary).where(Vocabulary.difficulty_level.in_(['A1', 'A2']))
        vocab_result = await session.execute(vocab_query)
        all_words = vocab_result.scalars().all()
        
        # Get user's learning stats
        stats_query = select(WordLearningStats).where(WordLearningStats.user_id == user.id)
        stats_result = await session.execute(stats_query)
        stats_map = {s.word_id: s for s in stats_result.scalars().all()}
        
        # Filter words based on filter_type
        filtered_words = []
        for word in all_words:
            stats = stats_map.get(word.id)
            
            if filter_type == "all":
                filtered_words.append((word, stats))
            elif filter_type == "known":
                if stats and stats.know_count >= 3 and stats.dont_know_count == 0:
                    filtered_words.append((word, stats))
            elif filter_type == "learning":
                if stats and (stats.know_count > 0 or stats.dont_know_count > 0):
                    if not (stats.know_count >= 3 and stats.dont_know_count == 0):
                        filtered_words.append((word, stats))
            elif filter_type == "new":
                if not stats:
                    filtered_words.append((word, None))
        
        # Pagination
        total_words = len(filtered_words)
        total_pages = ceil(total_words / WORDS_PER_PAGE) if total_words > 0 else 1
        start_idx = page * WORDS_PER_PAGE
        end_idx = start_idx + WORDS_PER_PAGE
        page_words = filtered_words[start_idx:end_idx]
        
        # Build text
        filter_names = {
            "all": "Всі слова",
            "known": "Знаю",
            "learning": "Вивчаю",
            "new": "Нові"
        }
        
        text = f"📖 <b>{filter_names.get(filter_type, 'Словник')}</b>\n\n"
        text += f"Всього: <b>{total_words}</b> слів\n\n"
        
        if not page_words:
            text += "😔 Немає слів у цій категорії.\n\n"
            if filter_type == "new":
                text += "Всі доступні слова вже додані до вивчення!"
        else:
            for word, stats in page_words:
                # Status emoji
                if not stats:
                    status = "🆕"
                elif stats.know_count >= 3 and stats.dont_know_count == 0:
                    status = "✅"
                else:
                    status = "📖"
                
                text += f"{status} <b>{word.word_polish}</b> - {word.translation_ua}\n"
                
                if stats:
                    text += f"   📊 Знаю: {stats.know_count} | Не знаю: {stats.dont_know_count}\n"
                
                text += "\n"
            
            text += f"\n<i>Натисни на фільтр щоб переключитися</i>"
    
    await state.update_data(vocab_page=page)
    
    keyboard = get_vocabulary_browser_keyboard(page=page, total_pages=total_pages, filter_type=filter_type)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "vocab_noop")
async def vocab_noop(callback: CallbackQuery):
    """No-op for pagination display."""
    await callback.answer()


@router.callback_query(F.data == "vocab_add_word")
async def add_custom_word(callback: CallbackQuery, state: FSMContext):
    """Start process of adding custom word."""
    text = (
        "➕ <b>Додавання слова</b>\n\n"
        "Ця функція буде доступна в наступній версії!\n\n"
        "Поки що ти можеш вивчати 40 стартових слів. 📚"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙", callback_data="vocabulary_browser")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("vocab_remove_"))
async def remove_word_from_learning(callback: CallbackQuery, state: FSMContext):
    """Remove word from user's learning list."""
    word_id = int(callback.data.replace("vocab_remove_", ""))
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Delete stats
        stats_query = select(WordLearningStats).where(
            WordLearningStats.user_id == user.id,
            WordLearningStats.word_id == word_id
        )
        stats_result = await session.execute(stats_query)
        stats = stats_result.scalar_one_or_none()
        
        if stats:
            await session.delete(stats)
            await session.commit()
            await callback.answer("🗑️ Слово видалено зі списку!", show_alert=True)
        else:
            await callback.answer("❌ Слово не знайдено", show_alert=True)
    
    # Return to vocabulary browser
    await show_vocabulary_browser(callback, state)


@router.callback_query(F.data.startswith("vocab_add_"))
async def add_word_to_learning(callback: CallbackQuery, state: FSMContext):
    """Add word to user's learning list."""
    word_id = int(callback.data.replace("vocab_add_", ""))
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Check if already exists
        stats_query = select(WordLearningStats).where(
            WordLearningStats.user_id == user.id,
            WordLearningStats.word_id == word_id
        )
        stats_result = await session.execute(stats_query)
        existing = stats_result.scalar_one_or_none()
        
        if not existing:
            # Create new stats
            stats = WordLearningStats(
                user_id=user.id,
                word_id=word_id,
                priority_score=100.0
            )
            session.add(stats)
            await session.commit()
            await callback.answer("✅ Слово додано до вивчення!", show_alert=True)
        else:
            await callback.answer("ℹ️ Слово вже у твоєму списку", show_alert=True)
    
    # Return to vocabulary browser
    await show_vocabulary_browser(callback, state)
