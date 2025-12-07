"""Settings handlers for user preferences."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import models
from models.models import User
from utils.states import Settings, MainMenu
from utils.keyboards import get_settings_keyboard, get_level_selection_keyboard

router = Router()


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    """Show settings menu."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
    
    await state.set_state(Settings.main)
    
    text = "⚙️ <b>Settings</b>\n\nAdjust your learning preferences:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(user.level),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "change_level", Settings.main)
async def change_level_menu(callback: CallbackQuery, state: FSMContext):
    """Show level selection menu."""
    await state.set_state(Settings.change_level)
    
    text = (
        "📊 <b>Change Your Level</b>\n\n"
        "Select your Polish proficiency level:\n\n"
        "🟢 <b>A1</b> - Complete beginner\n"
        "🟡 <b>A2</b> - Elementary\n"
        "🟠 <b>B1</b> - Intermediate"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_level_selection_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("level_"), Settings.change_level)
async def set_level(callback: CallbackQuery, state: FSMContext):
    """Set user level."""
    level = callback.data.split("_")[1]  # A1, A2, or B1
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        user.level = level
        await session.commit()
    
    await state.set_state(MainMenu.menu)
    
    await callback.answer(f"✅ Level changed to {level}", show_alert=True)
    await show_settings(callback, state)


@router.callback_query(F.data == "my_progress")
async def show_progress(callback: CallbackQuery, state: FSMContext):
    """Show user progress and statistics."""
    from services.srs_service import srs_service
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        stats = await srs_service.get_review_stats(session, user.id)
    
    text = (
        f"📊 <b>Your Progress</b>\n\n"
        f"🎚 Level: <b>{user.level}</b>\n"
        f"🔥 Streak: <b>{user.streak_days} days</b>\n\n"
        f"📚 <b>Vocabulary Statistics:</b>\n"
        f"   • Total Words: {stats['total_words']}\n"
        f"   • ⏰ Due Today: {stats['due_now']}\n"
        f"   • ✅ Mastered: {stats['mastered']}\n"
        f"   • 📖 Learning: {stats['learning']}\n"
        f"   • 🆕 New: {stats['new']}\n\n"
        "Keep up the excellent work! 💪"
    )
    
    from utils.keyboards import get_main_menu_keyboard
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()
