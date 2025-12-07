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
                "👋 <b>Witaj! Welcome to EasyPolska!</b>\n\n"
                "I'm your Polish learning companion, designed specifically for Ukrainian and Russian speakers.\n\n"
                "🎯 <b>Survival Mode</b>: Learn through real-life scenarios\n"
                "📚 <b>Review Words</b>: Smart spaced repetition system\n"
                "📊 <b>My Progress</b>: Track your learning journey\n\n"
                "Let's start your Polish adventure! 🇵🇱"
            )
        else:
            welcome_text = (
                f"👋 Welcome back, {message.from_user.first_name}!\n\n"
                f"Your current level: <b>{user.level}</b>\n"
                f"Streak: <b>{user.streak_days} days</b> 🔥\n\n"
                "Ready to continue learning? 🚀"
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
        "ℹ️ <b>EasyPolska Bot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/stats - View your learning statistics\n"
        "/menu - Return to main menu\n\n"
        "<b>How it works:</b>\n\n"
        "🎯 <b>Survival Mode</b>\n"
        "Learn Polish through real-life scenarios like shopping, ordering food, or using public transport. "
        "Each scenario includes audio pronunciation and challenging quizzes designed specifically for Slavic speakers.\n\n"
        "📚 <b>Review Words</b>\n"
        "Our smart spaced repetition system ensures you never forget what you've learned. "
        "Words are reviewed at optimal intervals based on your performance.\n\n"
        "📊 <b>Progress Tracking</b>\n"
        "Keep track of your streak, vocabulary size, and mastery level.\n\n"
        "Need help? Contact @your_support_username"
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
            await message.answer("❌ Please use /start first!")
            return
        
        stats = await srs_service.get_review_stats(session, user.id)
    
    stats_text = (
        f"📊 <b>Your Learning Statistics</b>\n\n"
        f"🎚 Level: <b>{user.level}</b>\n"
        f"🔥 Streak: <b>{user.streak_days} days</b>\n\n"
        f"📚 <b>Vocabulary:</b>\n"
        f"   Total Words: {stats['total_words']}\n"
        f"   ⏰ Due Now: {stats['due_now']}\n"
        f"   ✅ Mastered: {stats['mastered']}\n"
        f"   📖 Learning: {stats['learning']}\n"
        f"   🆕 New: {stats['new']}\n\n"
        "Keep up the great work! 💪"
    )
    
    await message.answer(stats_text, parse_mode='HTML')


@router.message(Command("menu"))
@router.callback_query(F.data == "main_menu")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext):
    """Show main menu."""
    await state.set_state(MainMenu.menu)
    
    text = "🏠 <b>Main Menu</b>\n\nWhat would you like to do?"
    keyboard = get_main_menu_keyboard()
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await event.answer()
