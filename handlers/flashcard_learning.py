"""Handlers for flashcard-based vocabulary learning."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import models
from models.models import User
from utils.states import FlashcardLearning, MainMenu
from utils.keyboards import (
    get_flashcard_word_keyboard,
    get_flashcard_feedback_keyboard,
    get_main_menu_keyboard
)
from services.flashcard_service import flashcard_service

router = Router()


@router.callback_query(F.data == "flashcard_learning")
async def start_flashcard_learning(callback: CallbackQuery, state: FSMContext):
    """Start flashcard learning session."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Помилка: користувач не знайдений!", show_alert=True)
            return
        
        # Get learning stats
        stats = await flashcard_service.get_learning_stats(session, user.id)
    
    await state.set_state(FlashcardLearning.show_word)
    
    text = (
        "📚 <b>Вивчення Слів (Картки)</b>\n\n"
        f"📊 <b>Твоя Статистика:</b>\n"
        f"   ✅ Знаю: {stats['known_words']}\n"
        f"   📖 Вивчаю: {stats['learning_words']}\n"
        f"   🆕 Нові: {stats['new_words']}\n\n"
        "Натискай на кнопку щоб показати переклад, потім обери чи знаєш ти це слово.\n\n"
        "Готовий почати? 🚀"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Почати Навчання", callback_data="flashcard_show_next")],
        [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "flashcard_show_next", FlashcardLearning.show_word)
@router.callback_query(F.data == "flashcard_next")
async def show_next_word(callback: CallbackQuery, state: FSMContext):
    """Show next word card."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Get next word
        word_data = await flashcard_service.get_next_word_for_user(session, user.id)
        
        if not word_data:
            await callback.message.edit_text(
                "🎉 <b>Вітаю!</b>\n\nЗараз немає слів для вивчення!\n\n"
                "Спробуй пізніше або додай нові слова.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
            )
            await state.set_state(MainMenu.menu)
            await callback.answer()
            return
        
        word, stats = word_data
        
        # Save to state
        await state.update_data(
            current_word_id=word.id,
            current_stats_id=stats.id,
            word_polish=word.word_polish,
            word_ukrainian=word.translation_ua,
            word_example=word.example_sentence_pl
        )
    
    await state.set_state(FlashcardLearning.show_word)
    
    # Show word card (only Polish word initially)
    text = (
        "📖 <b>Слово:</b>\n\n"
        f"<b><i>{word.word_polish}</i></b>\n\n"
        "👇 Натисни кнопку щоб побачити переклад"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_flashcard_word_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "show_translation", FlashcardLearning.show_word)
async def show_translation(callback: CallbackQuery, state: FSMContext):
    """Show translation and example sentence."""
    data = await state.get_data()
    
    await state.set_state(FlashcardLearning.show_translation)
    
    # Build text with translation and example
    text = (
        f"🇵🇱 <b>{data['word_polish']}</b>\n"
        f"🇺🇦 <b>{data['word_ukrainian']}</b>\n\n"
    )
    
    if data.get('word_example'):
        text += f"<i>{data['word_example']}</i>\n\n"
    
    text += "Чи знаєш ти це слово?"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_flashcard_feedback_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "flashcard_know", FlashcardLearning.show_translation)
async def handle_know_button(callback: CallbackQuery, state: FSMContext):
    """Handle 'I know this word' button press."""
    data = await state.get_data()
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        await flashcard_service.update_word_stats(
            session,
            stats_id=data['current_stats_id'],
            knows_word=True
        )
    
    await callback.answer("✅ Чудово!", show_alert=False)
    
    # Show next word
    await show_next_word(callback, state)


@router.callback_query(F.data == "flashcard_dont_know", FlashcardLearning.show_translation)
async def handle_dont_know_button(callback: CallbackQuery, state: FSMContext):
    """Handle 'I don't know this word' button press."""
    data = await state.get_data()
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        await flashcard_service.update_word_stats(
            session,
            stats_id=data['current_stats_id'],
            knows_word=False
        )
    
    await callback.answer("📝 Повторимо пізніше!", show_alert=False)
    
    # Show next word
    await show_next_word(callback, state)
