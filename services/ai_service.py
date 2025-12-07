"""AI service for generating quiz questions and content using Groq API."""

import json
import asyncio
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from groq import AsyncGroq
import config
from utils.prompts import (
    QUIZ_SYSTEM_PROMPT,
    QUIZ_DIFFICULTY_HARD,
    QUIZ_DIFFICULTY_NORMAL,
    FILL_IN_BLANK_PROMPT,
    SCENARIO_INTRO_PROMPT
)


class QuizData(BaseModel):
    """Validated quiz question data structure."""
    question: str = Field(..., min_length=10, max_length=500)
    correct_answer: str = Field(..., min_length=1, max_length=200)
    distractor_1: str = Field(..., min_length=1, max_length=200)
    distractor_2: str = Field(..., min_length=1, max_length=200)
    distractor_3: str = Field(..., min_length=1, max_length=200)
    explanation: str = Field(..., min_length=20, max_length=1000)


class FillInBlankData(BaseModel):
    """Validated fill-in-the-blank question data."""
    sentence: str = Field(..., min_length=10, max_length=500)
    correct_answer: str = Field(..., min_length=1, max_length=100)
    distractor_1: str = Field(..., min_length=1, max_length=100)
    distractor_2: str = Field(..., min_length=1, max_length=100)
    distractor_3: str = Field(..., min_length=1, max_length=100)
    explanation: str = Field(..., min_length=10, max_length=500)


class ScenarioIntroData(BaseModel):
    """Validated scenario introduction data."""
    intro_pl: str = Field(..., min_length=20, max_length=500)
    intro_ua: str = Field(..., min_length=20, max_length=500)
    intro_ru: str = Field(..., min_length=20, max_length=500)


class AIService:
    """Service for AI-powered content generation."""
    
    def __init__(self):
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL
        self.temperature = config.GROQ_TEMPERATURE
        self.max_tokens = config.GROQ_MAX_TOKENS
    
    async def _make_request(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """Make API request with retry logic."""
        for attempt in range(max_retries):
            try:
                print(f"🤖 AI API запит (спроба {attempt + 1}/{max_retries})...")
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    timeout=60.0  # Increased timeout
                )
                
                content = response.choices[0].message.content
                print(f"✅ AI відповідь отримана (довжина: {len(content)} символів)")
                return content
            
            except asyncio.TimeoutError as e:
                print(f"⏱️ Timeout помилка (спроба {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Очікування {wait_time}с перед повторною спробою...")
                    await asyncio.sleep(wait_time)
                else:
                    print("❌ Всі спроби вичерпано через timeout")
                    return None
            
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ AI API помилка (спроба {attempt + 1}/{max_retries}): {type(e).__name__}")
                print(f"   Деталі: {error_msg}")
                
                # Check if it's a rate limit error
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    print("🚫 Rate limit досягнуто, очікування довше...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(10)
                elif attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"❌ Всі спроби вичерпано. Остання помилка: {error_msg}")
                    return None
        
        return None
    
    async def generate_quiz(
        self,
        situation: str,
        situation_description: str,
        user_level: str = "A1",
        difficulty: str = "normal"
    ) -> Optional[QuizData]:
        """
        Generate a quiz question for a given situation.
        
        Args:
            situation: Title of the scenario (e.g., "At Żabka")
            situation_description: Detailed context for the scenario
            user_level: A1, A2, or B1
            difficulty: "normal" or "hard"
        
        Returns:
            QuizData object or None if generation failed
        """
        difficulty_instruction = (
            QUIZ_DIFFICULTY_HARD if difficulty == "hard" 
            else QUIZ_DIFFICULTY_NORMAL
        )
        
        system_prompt = QUIZ_SYSTEM_PROMPT.format(
            situation=situation,
            level=user_level,
            difficulty=difficulty,
            difficulty_instruction=difficulty_instruction
        )
        
        user_prompt = f"Generate a quiz question for: {situation_description}"
        
        response = await self._make_request(system_prompt, user_prompt)
        
        if not response:
            print("❌ Failed to generate quiz question")
            return None
        
        try:
            data = json.loads(response)
            quiz = QuizData(**data)
            return quiz
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"❌ Failed to parse quiz data: {e}")
            print(f"Raw response: {response}")
            return None
    
    async def generate_fill_in_blank(
        self,
        word: str,
        translation_ua: str,
        translation_ru: str,
        user_level: str = "A1"
    ) -> Optional[FillInBlankData]:
        """
        Generate a fill-in-the-blank question for vocabulary review.
        
        Args:
            word: Polish word to test
            translation_ua: Ukrainian translation
            translation_ru: Russian translation
            user_level: A1, A2, or B1
        
        Returns:
            FillInBlankData object or None if generation failed
        """
        system_prompt = FILL_IN_BLANK_PROMPT.format(
            word=word,
            translation_ua=translation_ua,
            translation_ru=translation_ru,
            level=user_level
        )
        
        user_prompt = f"Create a fill-in-the-blank question for the word: {word}"
        
        response = await self._make_request(system_prompt, user_prompt)
        
        if not response:
            print("❌ Failed to generate fill-in-blank question")
            return None
        
        try:
            data = json.loads(response)
            question = FillInBlankData(**data)
            return question
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"❌ Failed to parse fill-in-blank data: {e}")
            return None
    
    async def generate_scenario_intro(
        self,
        situation: str,
        description: str,
        level: str = "A1"
    ) -> Optional[ScenarioIntroData]:
        """
        Generate introduction for a scenario in multiple languages.
        
        Args:
            situation: Scenario title
            description: Scenario description
            level: Difficulty level
        
        Returns:
            ScenarioIntroData or None if generation failed
        """
        system_prompt = SCENARIO_INTRO_PROMPT.format(
            situation=situation,
            description=description,
            level=level
        )
        
        user_prompt = "Generate the introduction"
        
        response = await self._make_request(system_prompt, user_prompt)
        
        if not response:
            return None
        
        try:
            data = json.loads(response)
            intro = ScenarioIntroData(**data)
            return intro
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"❌ Failed to parse scenario intro: {e}")
            return None


# Singleton instance
ai_service = AIService()
