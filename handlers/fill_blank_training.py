"""Handlers for fill-in-the-blank training mode."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import random

from models import models
from models.models import User
from utils.states import FillBlankTraining, MainMenu
from utils.keyboards import get_quiz_keyboard, get_main_menu_keyboard
from services.srs_service import srs_service
from services.ai_service import ai_service

router = Router()


@router.callback_query(F.data == "fill_blank_training")
async def start_fill_blank_training(callback: CallbackQuery, state: FSMContext):
    """Start fill-in-the-blank training session."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Помилка: користувач не знайдений!", show_alert=True)
            return
        
        # Get due words for practice
        due_words = await srs_service.get_due_words(session, user.id, limit=10)
        
        if not due_words:
            text = (
                "🎉 <b>Відмінна робота!</b>\n\n"
                "Зараз немає слів для тренування.\n"
                "Спробуй вивчити нові слова в режимі карток! 📚"
            )
            await callback.message.edit_text(
                text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
            )
            await callback.answer()
            return
        
        # Save to state
        await state.update_data(
            user_id=user.id,
            user_level=user.level,
            due_words_count=len(due_words),
            current_question=0,
            correct_answers=0
        )
    
    await state.set_state(FillBlankTraining.show_question)
    
    text = (
        "📝 <b>Тренування з Пропусками</b>\n\n"
        f"У тебе <b>{len(due_words)}</b> слово(ів) для тренування.\n\n"
        "AI згенерує речення з пропуском, а ти обереш правильне слово.\n"
        "Після відповіді отримаєш детальне пояснення українською! 🇺🇦\n\n"
        "Готовий? 🚀"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Почати Тренування", callback_data="show_fill_blank_question")],
        [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "show_fill_blank_question", FillBlankTraining.show_question)
@router.callback_query(F.data == "next_fill_blank")
async def show_fill_blank_question(callback: CallbackQuery, state: FSMContext):
    """Show fill-in-the-blank question."""
    data = await state.get_data()
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get due words
        due_words = await srs_service.get_due_words(session, data['user_id'], limit=10)
        
        current_q = data.get('current_question', 0)
        
        if current_q >= len(due_words):
            # Training complete
            await complete_training(callback, state)
            return
        
        progress = due_words[current_q]
        
        # Get word details
        from models.models import Vocabulary
        word_query = select(Vocabulary).where(Vocabulary.id == progress.word_id)
        word_result = await session.execute(word_query)
        word = word_result.scalar_one()
    
    await callback.message.edit_text("⏳ Генерую питання...", parse_mode='HTML')
    await callback.answer()
    
    # Generate fill-in-the-blank question with better explanation
    question_data = await ai_service.generate_fill_in_blank(
        word=word.word_polish,
        translation_ua=word.translation_ua,
        translation_ru=word.translation_ru,
        user_level=data.get('user_level', 'A1')
    )
    
    if not question_data:
        await callback.message.answer("❌ Помилка генерації питання. Пропускаю...")
        # Skip to next
        await state.update_data(current_question=current_q + 1)
        await show_fill_blank_question(callback, state)
        return
    
    # Shuffle answers
    answers = [
        question_data.correct_answer,
        question_data.distractor_1,
        question_data.distractor_2,
        question_data.distractor_3
    ]
    random.shuffle(answers)
    correct_index = answers.index(question_data.correct_answer)
    
    # Save to state
    await state.update_data(
        progress_id=progress.id,
        word_polish=word.word_polish,
        question_sentence=question_data.sentence,
        fill_blank_answers=answers,
        fill_blank_correct_index=correct_index,
        fill_blank_explanation=question_data.explanation,
        total_questions=len(due_words)
    )
    
    progress_text = f"Питання: {current_q + 1}/{len(due_words)}"
    question_text = (
        f"📝 <b>{progress_text}</b>\n\n"
        f"Заповни пропуск:\n\n"
        f"<i>{question_data.sentence}</i>"
    )
    
    await callback.message.answer(
        question_text,
        reply_markup=get_quiz_keyboard(answers, "fill_blank"),
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith("fill_blank_"), FillBlankTraining.show_question)
async def answer_fill_blank(callback: CallbackQuery, state: FSMContext):
    """Handle fill-in-the-blank answer."""
    answer_index = int(callback.data.split("_")[2])
    data = await state.get_data()
    
    is_correct = (answer_index == data['fill_blank_correct_index'])
    
    # Update SRS progress
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        quality = 4 if is_correct else 1
        await srs_service.update_progress(
            session=session,
            progress_id=data['progress_id'],
            quality=quality,
            is_correct=is_correct
        )
    
    # Update stats
    if is_correct:
        await state.update_data(correct_answers=data.get('correct_answers', 0) + 1)
    
    await state.set_state(FillBlankTraining.show_result)
    
    if is_correct:
        feedback = (
            "✅ <b>Правильно!</b> Świetnie! 🎉\n\n"
            f"<b>Слово:</b> {data['word_polish']}\n\n"
            f"<b>Пояснення:</b>\n<i>{data['fill_blank_explanation']}</i>"
        )
    else:
        feedback = (
            f"❌ <b>Не зовсім.</b>\n\n"
            f"Твоя відповідь: {data['fill_blank_answers'][answer_index]}\n"
            f"Правильна відповідь: <b>{data['fill_blank_answers'][data['fill_blank_correct_index']]}</b>\n\n"
            f"<b>Пояснення:</b>\n<i>{data['fill_blank_explanation']}</i>"
        )
    
    # Move to next question
    current_q = data.get('current_question', 0) + 1
    await state.update_data(current_question=current_q)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if current_q < data['total_questions']:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Наступне Питання", callback_data="next_fill_blank")],
            [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершити Тренування", callback_data="complete_fill_blank")],
            [InlineKeyboardButton(text="🔙 Головне Меню", callback_data="main_menu")]
        ])
    
    await state.set_state(FillBlankTraining.show_question)
    
    await callback.message.edit_text(
        feedback,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "complete_fill_blank")
async def complete_training(callback: CallbackQuery, state: FSMContext):
    """Complete training session and show results."""
    data = await state.get_data()
    
    total = data.get('total_questions', 0)
    correct = data.get('correct_answers', 0)
    percentage = (correct / total * 100) if total > 0 else 0
    
    text = (
        "🎉 <b>Тренування Завершено!</b>\n\n"
        f"📊 <b>Результати:</b>\n"
        f"   Правильних відповідей: <b>{correct}/{total}</b>\n"
        f"   Відсоток: <b>{percentage:.1f}%</b>\n\n"
    )
    
    if percentage >= 80:
        text += "🌟 Відмінна робота! Ти молодець!"
    elif percentage >= 60:
        text += "👍 Добре! Продовжуй навчання!"
    else:
        text += "💪 Не здавайся! Практика – шлях до успіху!"
    
    await state.set_state(MainMenu.menu)
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()
