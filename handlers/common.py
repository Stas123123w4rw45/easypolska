"""Common handlers for /start, /help, and basic commands."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import models
from models.models import User
from utils.states import MainMenu, FlashcardLearning
from utils.keyboards import get_main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Create or get user
        user_query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                level='A1'
            )
            session.add(user)
            await session.commit()
            
            welcome_text = (
                f"Привіт, <b>{message.from_user.first_name}</b>! 👋\n\n"
                "Я допоможу тобі вивчити польську мову! 🇵🇱\n\n"
                "Обери режим нижче:"
            )
        else:
            welcome_text = (
                f"Серія: <b>{user.streak_days} днів</b> 🔥\n\n"
                "Готовий продовжити навчання? 🚀"
            )
    
    await state.set_state(MainMenu.menu)
    
    # Send main menu with bottom keyboard
    from utils.keyboards import get_bottom_menu_keyboard
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    
    # Set persistent bottom menu
    await message.answer(
        "🔹 Використовуй кнопки внизу для швидкої навігації",
        reply_markup=get_bottom_menu_keyboard()
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


@router.callback_query(F.data == "my_progress")
async def show_progress(callback: CallbackQuery, state: FSMContext):
    """Show user progress and statistics."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ User not found!", show_alert=True)
            return
        
        # Get vocabulary stats
        from services.flashcard_service import flashcard_service
        stats = await flashcard_service.get_learning_stats(session, user.id)
        
        # Get SRS stats
        from services.srs_service import srs_service
        due_count = len(await srs_service.get_due_words(session, user.id))
        
        text = (
            f"📊 <b>Твій Прогрес</b>\n\n"
            f"🎯 <b>Рівень:</b> {user.level}\n\n"
            f"📚 <b>Словник:</b>\n"
            f"   ✅ Знаю: {stats['known_words']}\n"
            f"   📖 Вивчаю: {stats['learning_words']}\n"
            f"   🆕 Нові: {stats['new_words']}\n\n"
            f"🔄 <b>Повторення:</b>\n"
            f"   📝 До повторення: {due_count} слів\n\n"
            "Продовжуй навчання! 💪"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
    await callback.answer()


# Bottom menu handlers
@router.message(F.text == "🏠")
async def handle_home_button(message: Message, state: FSMContext):
    """Handle home button from bottom menu."""
    await state.clear()
    await cmd_start(message, state)


@router.message(F.text == "📚")
async def handle_flashcard_button(message: Message, state: FSMContext):
    """Handle flashcard button from bottom menu."""
    # Create fake callback for reusing existing handler
    from aiogram.types import User as TgUser
    from handlers import flashcard_learning
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Помилка!")
            return
        
        from services.flashcard_service import flashcard_service
        stats = await flashcard_service.get_learning_stats(session, user.id)
    
    await state.set_state(FlashcardLearning.show_word)
    
    text = (
        "📚 <b>Вивчення Слів (Картки)</b>\n\n"
        f"📊 <b>Твоя Статистика:</b>\n"
        f"   ✅ Знаю: {stats['known_words']}\n"
        f"   📖 Вивчаю: {stats['learning_words']}\n"
        f"   🆕 Нові: {stats['new_words']}\n\n"
        "Готовий почати? 🚀"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Почати", callback_data="flashcard_show_next")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')


@router.message(F.text == "📝")
async def handle_training_button(message: Message, state: FSMContext):
    """Handle training button from bottom menu."""
    # Redirect to fill blank training
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Тренування з пропусками", callback_data="fill_blank_training")],
        [InlineKeyboardButton(text="🎯 Режим виживання", callback_data="survival_mode")]
    ])
    
    await message.answer(
        "📝 <b>Вибери тип тренування:</b>",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@router.message(F.text == "📊")
async def handle_progress_button(message: Message, state: FSMContext):
    """Handle progress button from bottom menu."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Помилка!")
            return
        
        from services.flashcard_service import flashcard_service
        stats = await flashcard_service.get_learning_stats(session, user.id)
        
        from services.srs_service import srs_service
        due_count = len(await srs_service.get_due_words(session, user.id))
        
        text = (
            f"📊 <b>Твій Прогрес</b>\n\n"
            f"🎯 <b>Рівень:</b> {user.level}\n\n"
            f"📚 <b>Словник:</b>\n"
            f"   ✅ Знаю: {stats['known_words']}\n"
            f"   📖 Вивчаю: {stats['learning_words']}\n"
            f"   🆕 Нові: {stats['new_words']}\n\n"
            f"🔄 <b>Повторення:</b>\n"
            f"   📝 До повторення: {due_count} слів\n\n"
            "Продовжуй навчання! 💪"
        )
        
        await message.answer(text, parse_mode='HTML')


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
