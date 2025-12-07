"""Handlers for SRS (Spaced Repetition System) review."""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import models
from models.models import User, UserProgress, Vocabulary
from utils.states import SRSReview, MainMenu
from utils.keyboards import (
    get_review_start_keyboard,
    get_quiz_keyboard,
    get_main_menu_keyboard
)
from services.srs_service import srs_service
from services.ai_service import ai_service

router = Router()


@router.callback_query(F.data == "review_words")
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Start SRS review session."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Get due words
        due_words = await srs_service.get_due_words(session, user.id)
        due_count = len(due_words)
    
    if due_count == 0:
        text = (
            "🎉 <b>Відмінна робота!</b>\n\n"
            "Зараз немає слів для повторення. Усі твої слова актуальні!\n\n"
            "Спробуй вивчити нові слова в Режимі Виживання. 🎯"
        )
    else:
        text = (
            f"📚 <b>Час Повторення!</b>\n\n"
            f"У тебе <b>{due_count}</b> слово(ів) для повторення.\n\n"
            "Тримай свій словник свіжим! 💪"
        )
    
    await state.update_data(user_id=user.id, due_count=due_count, current_index=0)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_review_start_keyboard(due_count),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "start_review")
async def show_review_question(callback: CallbackQuery, state: FSMContext):
    """Show next review question."""
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get due words
        due_words = await srs_service.get_due_words(session, data['user_id'])
        
        if current_index >= len(due_words):
            # Session complete
            await complete_review_session(callback, state)
            return
        
        progress = due_words[current_index]
        
        # Get word details
        word_query = select(Vocabulary).where(Vocabulary.id == progress.word_id)
        word_result = await session.execute(word_query)
        word = word_result.scalar_one()
    
    await state.set_state(SRSReview.review_active)
    await callback.message.edit_text("⏳ Генерую питання...")
    await callback.answer()
    
    # Generate fill-in-the-blank question
    question_data = await ai_service.generate_fill_in_blank(
        word=word.word_polish,
        translation_ua=word.translation_ua,
        translation_ru=word.translation_ru,
        user_level=data.get('user_level', 'A1')
    )
    
    if not question_data:
        await callback.message.answer(
            "❌ Помилка генерації питання. Пропускаю...",
        )
        # Skip to next word
        await state.update_data(current_index=current_index + 1)
        await show_review_question(callback, state)
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
        review_answers=answers,
        review_correct_index=correct_index,
        review_explanation=question_data.explanation,
        total_words=len(due_words)
    )
    
    progress_text = f"Прогрес: {current_index + 1}/{len(due_words)}"
    question_text = (
        f"📝 <b>{progress_text}</b>\n\n"
        f"Заповни пропуск:\n\n"
        f"<i>{question_data.sentence}</i>"
    )
    
    await callback.message.answer(
        question_text,
        reply_markup=get_quiz_keyboard(answers, "review"),
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith("review_"), SRSReview.review_active)
async def answer_review(callback: CallbackQuery, state: FSMContext):
    """Handle review answer."""
    answer_index = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    is_correct = (answer_index == data['review_correct_index'])
    
    # Determine quality (0-5) based on correctness
    if is_correct:
        quality = 4  # Correct with some hesitation (can be adjusted based on time/attempts)
    else:
        quality = 1  # Incorrect but familiar
    
    # Update SRS progress
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        await srs_service.update_progress(
            session=session,
            progress_id=data['progress_id'],
            quality=quality,
            is_correct=is_correct
        )
    
    await state.set_state(SRSReview.show_result)
    
    if is_correct:
        feedback = (
            "✅ <b>Правильно!</b> Świetnie!\n\n"
            f"Слово: <b>{data['word_polish']}</b>\n\n"
            f"<i>{data['review_explanation']}</i>"
        )
    else:
        feedback = (
            f"❌ <b>Не зовсім.</b>\n\n"
            f"Правильна відповідь: <b>{data['review_answers'][data['review_correct_index']]}</b>\n\n"
            f"<i>{data['review_explanation']}</i>"
        )
    
    # Move to next question
    current_index = data.get('current_index', 0) + 1
    await state.update_data(current_index=current_index)
    
    keyboard = get_main_menu_keyboard() if current_index >= data['total_words'] else None
    
    if current_index < data['total_words']:
        from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Next Word", callback_data="start_review")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Complete Session", callback_data="complete_review")]
        ])
    
    await callback.message.edit_text(
        feedback,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "complete_review")
async def complete_review_session(callback: CallbackQuery, state: FSMContext):
    """Complete review session and show results."""
    data = await state.get_data()
    
    text = (
        "🎉 <b>Сесія Повторення Завершена!</b>\n\n"
        f"Ти повторив <b>{data.get('total_words', 0)}</b> слово(ів).\n\n"
        "Відмінна робота! Тримай свою серію! 🔥"
    )
    
    await state.set_state(MainMenu.menu)
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()
