"""Finite State Machine states for bot navigation."""

from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    """Main menu states."""
    menu = State()


class SurvivalMode(StatesGroup):
    """Survival mode (scenario-based learning) states."""
    select_scenario = State()
    scenario_intro = State()
    preview_vocabulary = State()
    quiz_active = State()
    show_feedback = State()


class SRSReview(StatesGroup):
    """SRS vocabulary review states."""
    review_active = State()
    show_result = State()
    session_complete = State()


class Settings(StatesGroup):
    """Settings menu states."""
    main = State()
    change_level = State()
