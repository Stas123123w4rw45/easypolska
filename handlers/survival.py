"""Handlers for Survival Mode (scenario-based learning)."""

import json
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models.models import User, Situation, UserQuizHistory, async_session_maker
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
    async with async_session_maker() as session:
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
            await callback.answer("No scenarios available yet!", show_alert=True)
            return
        
        scenarios_data = [
            {"id": s.id, "title": s.title, "level": s.level}
            for s in scenarios
        ]
    
    await state.set_state(SurvivalMode.select_scenario)
    
    text = (
        "🎯 <b>Survival Mode</b>\n\n"
        f"Choose a scenario to practice. These are real-life situations you'll encounter in Poland!\n\n"
        f"Your level: <b>{user.level}</b>"
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
    
    async with async_session_maker() as session:
        # Get scenario
        query = select(Situation).where(Situation.id == scenario_id)
        result = await session.execute(query)
        scenario = result.scalar_one_or_none()
        
        if not scenario:
            await callback.answer("Scenario not found!", show_alert=True)
            return
        
        # Save scenario to state
        await state.update_data(
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            scenario_description=scenario.description,
            scenario_level=scenario.level,
            scenario_context=scenario.context_prompt
        )
    
    await state.set_state(SurvivalMode.scenario_intro)
    
    # Show loading message
    await callback.message.edit_text("⏳ Preparing your scenario...")
    await callback.answer()
    
    # Generate intro (optional - can skip if TTS is not available)
    intro_text = (
        f"📍 <b>{scenario.title}</b>\n\n"
        f"{scenario.description}\n\n"
        f"Level: {scenario.level}\n\n"
        "Get ready for your quiz! 🎯"
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
        "Ready to start?",
        reply_markup=get_continue_keyboard("start_quiz")
    )


@router.callback_query(F.data == "start_quiz", SurvivalMode.scenario_intro)
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    """Generate and show quiz question."""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        # Get user
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Determine difficulty
        difficulty = "normal"
        # Could add logic here to check user's performance and adjust difficulty
    
    await callback.message.edit_text("🤔 Generating your quiz question...")
    await callback.answer()
    
    # Generate quiz
    quiz = await ai_service.generate_quiz(
        situation=data['scenario_title'],
        situation_description=data['scenario_context'],
        user_level=data['scenario_level'],
        difficulty=difficulty
    )
    
    if not quiz:
        await callback.message.answer(
            "❌ Sorry, couldn't generate a question. Please try again.",
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
    
    question_text = f"❓ <b>Question:</b>\n\n{quiz.question}"
    
    await callback.message.answer(
        question_text,
        reply_markup=get_quiz_keyboard(answers, "quiz"),
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith("quiz_"), SurvivalMode.quiz_active)
async def answer_quiz(callback: CallbackQuery, state: FSMContext):
    """Handle quiz answer."""
    answer_index = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    is_correct = (answer_index == data['quiz_correct_index'])
    
    # Save to history
    async with async_session_maker() as session:
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
            "✅ <b>Correct!</b> Świetnie! 🎉\n\n"
            f"<b>Explanation:</b>\n{data['quiz_explanation']}"
        )
    else:
        feedback = (
            f"❌ <b>Not quite right.</b>\n\n"
            f"Your answer: {data['quiz_answers'][answer_index]}\n"
            f"Correct answer: <b>{data['quiz_answers'][data['quiz_correct_index']]}</b>\n\n"
            f"<b>Explanation:</b>\n{data['quiz_explanation']}"
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
