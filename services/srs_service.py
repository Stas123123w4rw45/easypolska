"""Spaced Repetition System (SRS) service using SuperMemo-2 algorithm."""

from datetime import datetime, timedelta
from typing import Tuple, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import User, UserProgress, Vocabulary
import config


class SRSService:
    """Service for managing spaced repetition algorithm."""
    
    @staticmethod
    def calculate_next_review(
        quality: int,
        repetitions: int,
        easiness_factor: float,
        interval_days: int
    ) -> Tuple[int, float, int]:
        """
        Calculate next review time using SuperMemo-2 algorithm.
        
        Args:
            quality: User's recall quality (0-5)
                0 = complete blackout
                1 = incorrect but familiar
                2 = incorrect but remembered after seeing answer
                3 = correct with difficulty
                4 = correct with hesitation
                5 = perfect recall
            repetitions: Number of consecutive successful reviews
            easiness_factor: Easiness factor (>=1.3)
            interval_days: Current interval in days
        
        Returns:
            Tuple of (new_interval_days, new_easiness_factor, new_repetitions)
        """
        # If quality < 3, reset card (failed recall)
        if quality < 3:
            repetitions = 0
            interval_days = 0
        else:
            # Successful recall
            if repetitions == 0:
                interval_days = config.SRS_INITIAL_INTERVAL  # 1 day
            elif repetitions == 1:
                interval_days = config.SRS_GRADUATION_INTERVAL  # 6 days
            else:
                interval_days = round(interval_days * easiness_factor)
            
            repetitions += 1
        
        # Update easiness factor based on quality
        easiness_factor = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        easiness_factor = max(config.SRS_MIN_EASINESS, easiness_factor)
        
        return interval_days, easiness_factor, repetitions
    
    @staticmethod
    async def get_due_words(
        session: AsyncSession,
        user_id: int,
        limit: int = None
    ) -> List[UserProgress]:
        """
        Get words due for review for a user.
        
        Args:
            session: Database session
            user_id: User ID
            limit: Maximum number of words to return (default: config.MAX_REVIEWS_PER_SESSION)
        
        Returns:
            List of UserProgress objects
        """
        if limit is None:
            limit = config.MAX_REVIEWS_PER_SESSION
        
        now = datetime.utcnow()
        
        query = (
            select(UserProgress)
            .where(UserProgress.user_id == user_id)
            .where(UserProgress.next_review_time <= now)
            .order_by(UserProgress.next_review_time.asc())
            .limit(limit)
        )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update_progress(
        session: AsyncSession,
        progress_id: int,
        quality: int,
        is_correct: bool
    ) -> None:
        """
        Update user progress after review.
        
        Args:
            session: Database session
            progress_id: UserProgress ID
            quality: Recall quality (0-5)
            is_correct: Whether the answer was correct
        """
        query = select(UserProgress).where(UserProgress.id == progress_id)
        result = await session.execute(query)
        progress = result.scalar_one_or_none()
        
        if not progress:
            return
        
        # Calculate new SRS parameters
        interval_days, easiness_factor, repetitions = SRSService.calculate_next_review(
            quality=quality,
            repetitions=progress.repetitions,
            easiness_factor=progress.easiness_factor,
            interval_days=progress.interval_days
        )
        
        # Update progress
        progress.last_quality = quality
        progress.interval_days = interval_days
        progress.easiness_factor = easiness_factor
        progress.repetitions = repetitions
        progress.next_review_time = datetime.utcnow() + timedelta(days=interval_days)
        progress.last_reviewed = datetime.utcnow()
        progress.times_reviewed += 1
        
        if is_correct:
            progress.times_correct += 1
        else:
            progress.times_wrong += 1
        
        # Update SRS stage (0-5)
        progress.srs_stage = min(5, repetitions)
        
        await session.commit()
    
    @staticmethod
    async def add_word_to_user(
        session: AsyncSession,
        user_id: int,
        word_id: int
    ) -> Optional[UserProgress]:
        """
        Add a new word to user's learning queue.
        
        Args:
            session: Database session
            user_id: User ID
            word_id: Vocabulary word ID
        
        Returns:
            UserProgress object or None if already exists
        """
        # Check if already exists
        query = (
            select(UserProgress)
            .where(UserProgress.user_id == user_id)
            .where(UserProgress.word_id == word_id)
        )
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return None
        
        # Create new progress entry
        progress = UserProgress(
            user_id=user_id,
            word_id=word_id,
            srs_stage=0,
            next_review_time=datetime.utcnow(),  # Review immediately
            last_quality=0,
            repetitions=0,
            easiness_factor=2.5,
            interval_days=0
        )
        
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
        
        return progress
    
    @staticmethod
    async def get_review_stats(
        session: AsyncSession,
        user_id: int
    ) -> dict:
        """
        Get user's review statistics.
        
        Args:
            session: Database session
            user_id: User ID
        
        Returns:
            Dictionary with stats
        """
        query = select(UserProgress).where(UserProgress.user_id == user_id)
        result = await session.execute(query)
        all_progress = result.scalars().all()
        
        if not all_progress:
            return {
                "total_words": 0,
                "due_now": 0,
                "mastered": 0,
                "learning": 0,
                "new": 0
            }
        
        now = datetime.utcnow()
        
        stats = {
            "total_words": len(all_progress),
            "due_now": sum(1 for p in all_progress if p.next_review_time <= now),
            "mastered": sum(1 for p in all_progress if p.srs_stage >= 4),
            "learning": sum(1 for p in all_progress if 0 < p.srs_stage < 4),
            "new": sum(1 for p in all_progress if p.srs_stage == 0)
        }
        
        return stats


# Singleton instance
srs_service = SRSService()
