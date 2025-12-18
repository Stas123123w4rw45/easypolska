"""Handlers for Survival Mode (scenario-based learning)."""

import json
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import models
from models.models import User, Situation, UserQuizHistory
from utils.states import SurvivalMode, MainMenu
from utils.keyboards import (
    get_scenario_selection_keyboard,
    get_quiz_keyboard,
    get_continue_keyboard,
    get_main_menu_keyboard
)
from services.ai_service import ai_service
from services.tts_service import tts_service

router = Router()


@router.callback_query(F.data == "survival_mode")
async def start_survival_mode(callback: CallbackQuery, state: FSMContext):
    """Start survival mode - show scenario selection."""
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Get scenarios for user's level
        scenarios_query = select(Situation).where(
            Situation.is_active == True,
            Situation.level <= user.level
        )
        scenarios_result = await session.execute(scenarios_query)
        scenarios = scenarios_result.scalars().all()
        
        if not scenarios:
            await callback.answer("Сценаріїв поки немає!", show_alert=True)
            return
        
        scenarios_data = [
            {"id": s.id, "title": s.title, "level": s.level}
            for s in scenarios
        ]
    
    await state.set_state(SurvivalMode.select_scenario)
    
    text = (
        "🎯 <b>Режим Виживання</b>\n\n"
        f"Обери сценарій для практики. Це реальні життєві ситуації, з якими ти зіткнешся в Польщі!\n\n"
        f"Твій рівень: <b>{user.level}</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_scenario_selection_keyboard(scenarios_data),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("scenario_"), SurvivalMode.select_scenario)
async def select_scenario(callback: CallbackQuery, state: FSMContext):
    """Handle scenario selection."""
    scenario_id = int(callback.data.split("_")[1])
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get scenario
        query = select(Situation).where(Situation.id == scenario_id)
        result = await session.execute(query)
        scenario = result.scalar_one_or_none()
        
        if not scenario:
            await callback.answer("Сценарій не знайдено!", show_alert=True)
            return
        
        # Save scenario to state
        await state.update_data(
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            scenario_description=scenario.description,
            scenario_level=scenario.level,
            scenario_context=scenario.context_prompt,
            scenario_vocabulary=scenario.vocabulary_focus or []
        )
    
    await state.set_state(SurvivalMode.scenario_intro)
    
    # Show loading message
    await callback.message.edit_text("⏳ Готую твій сценарій...")
    await callback.answer()
    
    # Generate intro (optional - can skip if TTS is not available)
    intro_text = (
        f"📍 <b>{scenario.title}</b>\n\n"
        f"{scenario.description}\n\n"
        f"Рівень: {scenario.level}\n\n"
        "Готуйся до тесту! 🎯"
    )
    
    # Try to generate audio
    audio_path = None
    if tts_service.client:
        audio_path = await tts_service.generate_speech(scenario.description)
    
    if audio_path:
        audio = FSInputFile(audio_path)
        await callback.message.answer_audio(
            audio,
            caption=intro_text,
            parse_mode='HTML'
        )
    else:
        await callback.message.answer(intro_text, parse_mode='HTML')
    
    await callback.message.answer(
        "Готовий почати?",
        reply_markup=get_continue_keyboard("preview_vocabulary")
    )


@router.callback_query(F.data == "preview_vocabulary", SurvivalMode.scenario_intro)
async def preview_vocabulary(callback: CallbackQuery, state: FSMContext):
    """Show vocabulary preview before quiz."""
    data = await state.get_data()
    vocab_list = data.get('scenario_vocabulary', [])
    
    if not vocab_list:
        # If no vocabulary, skip to quiz
        await start_quiz(callback, state)
        return
    
    await state.set_state(SurvivalMode.preview_vocabulary)
    
    # Format vocabulary list
    vocab_text = "📚 <b>Словник для цього сценарію:</b>\n\n"
    for word in vocab_list:
        # Check if word has translation format "Word (Translation)" or just "Word"
        if "(" in word and ")" in word:
            vocab_text += f"🔹 {word}\n"
        else:
            vocab_text += f"🔹 {word}\n"
            
    vocab_text += "\nЗапам'ятай ці слова, вони зараз знадобляться!"
    
    await callback.message.edit_text(
        vocab_text,
        reply_markup=get_continue_keyboard("start_quiz"),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "start_quiz", SurvivalMode.preview_vocabulary)
@router.callback_query(F.data == "start_quiz", SurvivalMode.scenario_intro)  # Fallback
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    """Generate and show quiz question."""
    data = await state.get_data()
    vocab_list = data.get('scenario_vocabulary', [])
    
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Add vocabulary to SRS if it exists
        # We need to find or create these words in Vocabulary table first
        from models.models import Vocabulary
        from services.srs_service import srs_service
        
        if vocab_list:
            for item in vocab_list:
                # Extract Polish word if format is "Polish (Ukrainian)"
                polish_word = item.split("(")[0].strip() if "(" in item else item.strip()
                
                # Check if word exists in DB
                v_query = select(Vocabulary).where(Vocabulary.word_polish == polish_word)
                v_result = await session.execute(v_query)
                vocab_item = v_result.scalar_one_or_none()
                
                if not vocab_item:
                    # Create new vocabulary item
                    # Try to extract translation if present
                    translation = ""
                    if "(" in item and ")" in item:
                        translation = item.split("(")[1].replace(")", "").strip()
                    
                    vocab_item = Vocabulary(
                        word_polish=polish_word,
                        translation_ua=translation,
                        translation_ru=translation,  # Fill required field
                        difficulty_level=data['scenario_level'],
                        category='scenario'
                    )
                    session.add(vocab_item)
                    await session.flush()  # Get ID
                
                # Add to SRS service for user
                await srs_service.add_word_to_user(session, user.id, vocab_item.id)
            
            await session.commit()
        
        # Determine difficulty
        difficulty = "normal"
        # Could add logic here to check user's performance and adjust difficulty
    
    await callback.message.edit_text("🤔 Генерую питання для тебе...")
    await callback.answer()
    
    # Generate quiz
    quiz = await ai_service.generate_quiz(
        situation=data['scenario_title'],
        situation_description=data['scenario_context'],
        user_level=data['scenario_level'],
        difficulty=difficulty,
        target_vocabulary=vocab_list
    )
    
    if not quiz:
        await callback.message.answer(
            "❌ Вибач, не вдалося згенерувати питання. Спробуй ще раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.set_state(MainMenu.menu)
        return
    
    # Shuffle answers
    answers = [
        quiz.correct_answer,
        quiz.distractor_1,
        quiz.distractor_2,
        quiz.distractor_3
    ]
    random.shuffle(answers)
    correct_index = answers.index(quiz.correct_answer)
    
    # Save quiz data to state
    await state.update_data(
        quiz_question=quiz.question,
        quiz_answers=answers,
        quiz_correct_index=correct_index,
        quiz_explanation=quiz.explanation,
        user_id=user.id
    )
    
    await state.set_state(SurvivalMode.quiz_active)
    
    question_text = f"❓ <b>Питання:</b>\n\n{quiz.question}"
    
    await callback.message.answer(
        question_text,
        reply_markup=get_quiz_keyboard(answers, "quiz", show_cancel=True),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "quiz_cancel", SurvivalMode.quiz_active)
async def cancel_quiz(callback: CallbackQuery, state: FSMContext):
    """Cancel quiz and return to main menu."""
    text = (
        "🚫 <b>Тренування скасовано</b>\n\n"
        "Прогрес не збережено.\n"
        "Можеш спробувати ще раз коли будеш готовий!"
    )
    
    await state.set_state(MainMenu.menu)
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quiz_"), SurvivalMode.quiz_active)
async def answer_quiz(callback: CallbackQuery, state: FSMContext):
    """Handle quiz answer."""
    answer_index = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    is_correct = (answer_index == data['quiz_correct_index'])
    
    # Save to history
    session_maker = models.get_session_maker()
    async with session_maker() as session:
        history = UserQuizHistory(
            user_id=data['user_id'],
            situation_id=data['scenario_id'],
            question=data['quiz_question'],
            user_answer=data['quiz_answers'][answer_index],
            correct_answer=data['quiz_answers'][data['quiz_correct_index']],
            is_correct=is_correct
        )
        session.add(history)
        await session.commit()
    
    await state.set_state(SurvivalMode.show_feedback)
    
    if is_correct:
        feedback = (
            "✅ <b>Правильно!</b> Świetnie! 🎉\n\n"
            f"<b>Пояснення:</b>\n{data['quiz_explanation']}"
        )
    else:
        feedback = (
            f"❌ <b>Не зовсім правильно.</b>\n\n"
            f"Твоя відповідь: {data['quiz_answers'][answer_index]}\n"
            f"Правильна відповідь: <b>{data['quiz_answers'][data['quiz_correct_index']]}</b>\n\n"
            f"<b>Пояснення:</b>\n{data['quiz_explanation']}"
        )
    
    await callback.message.edit_text(
        feedback,
        reply_markup=get_continue_keyboard("continue_survival"),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "continue_survival", SurvivalMode.show_feedback)
async def continue_survival(callback: CallbackQuery, state: FSMContext):
    """Continue with another question or return to menu."""
    # For now, return to scenario selection
    # Could add logic to generate more questions for same scenario
    await start_survival_mode(callback, state)
