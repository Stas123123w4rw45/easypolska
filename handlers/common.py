"""Common handlers for /start, /help, and basic commands."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import models
from models.models import User
from utils.states import MainMenu
from utils.keyboards import get_main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Check if user exists
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                level='A1'
            )
            session.add(user)
            await session.commit()
            
            welcome_text = (
                "👋 <b>Вітаю! Ласкаво просимо до EasyPolska!</b>\n\n"
                "Я твій помічник у вивченні польської мови, спеціально розроблений для українців та росіян.\n\n"
                "🎯 <b>Режим Виживання</b>: Вчися через реальні життєві ситуації\n"
                "📚 <b>Повторити Слова</b>: Розумна система інтервального повторення\n"
                "📊 <b>Мій Прогрес</b>: Відстежуй свій прогрес у навчанні\n\n"
                "Почнімо твою польську пригоду! 🇵🇱"
            )
        else:
            welcome_text = (
                f"👋 З поверненням, {message.from_user.first_name}!\n\n"
                f"Твій поточний рівень: <b>{user.level}</b>\n"
                f"Серія: <b>{user.streak_days} днів</b> 🔥\n\n"
                "Готовий продовжити навчання? 🚀"
            )
    
    await state.set_state(MainMenu.menu)
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = (
        "ℹ️ <b>Допомога EasyPolska Bot</b>\n\n"
        "<b>Команди:</b>\n"
        "/start - Запустити бота\n"
        "/help - Показати цю допомогу\n"
        "/stats - Переглянути статистику навчання\n"
        "/menu - Повернутися до головного меню\n\n"
        "<b>Як це працює:</b>\n\n"
        "🎯 <b>Режим Виживання</b>\n"
        "Вчи польську через реальні життєві ситуації: покупки, замовлення їжі, громадський транспорт. "
        "Кожна ситуація включає аудіо вимову та складні тести, розроблені спеціально для слов'ян.\n\n"
        "📚 <b>Повторення Слів</b>\n"
        "Наша розумна система інтервального повторення гарантує, що ти не забудеш вивчене. "
        "Слова повторюються в оптимальні інтервали на основі твоїх результатів.\n\n"
        "📊 <b>Відстеження Прогресу</b>\n"
        "Відстежуй свою серію, розмір словника та рівень володіння.\n\n"
        "Потрібна допомога? Напиши @your_support_username"
    )
    
    await message.answer(help_text, parse_mode='HTML')


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command."""
    from services.srs_service import srs_service
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Будь ласка, спочатку використай /start!")
            return
        
        stats = await srs_service.get_review_stats(session, user.id)
    
    stats_text = (
        f"📊 <b>Твоя Статистика Навчання</b>\n\n"
        f"🎚 Рівень: <b>{user.level}</b>\n"
        f"🔥 Серія: <b>{user.streak_days} днів</b>\n\n"
        f"📚 <b>Словник:</b>\n"
        f"   Всього Слів: {stats['total_words']}\n"
        f"   ⏰ До Повторення: {stats['due_now']}\n"
        f"   ✅ Засвоєно: {stats['mastered']}\n"
        f"   📖 Вивчається: {stats['learning']}\n"
        f"   🆕 Нові: {stats['new']}\n\n"
        "Продовжуй у тому ж дусі! 💪"
    )
    
    await message.answer(stats_text, parse_mode='HTML')


@router.message(Command("menu"))
@router.callback_query(F.data == "main_menu")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext):
    """Show main menu."""
    await state.set_state(MainMenu.menu)
    
    text = "🏠 <b>Головне Меню</b>\n\nЩо ти хочеш зробити?"
    keyboard = get_main_menu_keyboard()
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await event.answer()
