"""Service for flashcard-based vocabulary learning."""

from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Vocabulary, WordLearningStats


class FlashcardService:
    """Service for managing flashcard learning system."""
    
    @staticmethod
    async def get_next_word_for_user(
        session: AsyncSession,
        user_id: int,
        exclude_word_ids: list[int] = None
    ) -> Optional[tuple[Vocabulary, WordLearningStats]]:
        """
        Get next word to show to user based on priority algorithm.
        
        Priority calculation:
        - New words (never seen): priority = 100
        - Known words: priority = (dont_know_count * 3) - (know_count * 1) + (days_since_last_shown * 2)
        
        Args:
            session: Database session
            user_id: User ID
            exclude_word_ids: List of word IDs to exclude from selection
        
        Returns:
            Tuple of (Vocabulary, WordLearningStats) or None if no words available
        """
        exclude_word_ids = exclude_word_ids or []
        
        # Get all vocabulary words
        vocab_query = select(Vocabulary).where(Vocabulary.difficulty_level.in_(['A1', 'A2']))
        if exclude_word_ids:
            vocab_query = vocab_query.where(~Vocabulary.id.in_(exclude_word_ids))
        
        vocab_result = await session.execute(vocab_query)
        all_words = vocab_result.scalars().all()
        
        if not all_words:
            return None
        
        # Get user's learning stats for these words
        word_ids = [w.id for w in all_words]
        stats_query = select(WordLearningStats).where(
            WordLearningStats.user_id == user_id,
            WordLearningStats.word_id.in_(word_ids)
        )
        stats_result = await session.execute(stats_query)
        stats_map = {stat.word_id: stat for stat in stats_result.scalars().all()}
        
        # Calculate priority for each word
        word_priorities = []
        
        for word in all_words:
            stats = stats_map.get(word.id)
            
            if not stats:
                # New word - high priority
                priority = 100.0
                # Create stats entry
                stats = WordLearningStats(
                    user_id=user_id,
                    word_id=word.id,
                    priority_score=priority
                )
                session.add(stats)
            else:
                # Calculate priority based on performance
                days_since_shown = 0
                if stats.last_shown:
                    days_since_shown = (datetime.utcnow() - stats.last_shown).days
                
                priority = (
                    (stats.dont_know_count * 3.0)
                    - (stats.know_count * 1.0)
                    + (days_since_shown * 2.0)
                    + 10.0  # Base priority
                )
                priority = max(0.0, priority)  # Never negative
                
                # Update priority in stats
                stats.priority_score = priority
            
            word_priorities.append((word, stats, priority))
        
        # Sort by priority (highest first)
        word_priorities.sort(key=lambda x: x[2], reverse=True)
        
        # Return highest priority word
        if word_priorities:
            await session.commit()
            return word_priorities[0][0], word_priorities[0][1]
        
        return None
    
    @staticmethod
    async def update_word_stats(
        session: AsyncSession,
        stats_id: int,
        knows_word: bool
    ) -> None:
        """
        Update word statistics after user feedback.
        
        Args:
            session: Database session
            stats_id: WordLearningStats ID
            knows_word: True if user pressed green button, False for red
        """
        query = select(WordLearningStats).where(WordLearningStats.id == stats_id)
        result = await session.execute(query)
        stats = result.scalar_one_or_none()
        
        if not stats:
            return
        
        # Update counts
        if knows_word:
            stats.know_count += 1
        else:
            stats.dont_know_count += 1
        
        # Update last shown time
        stats.last_shown = datetime.utcnow()
        
        # SMART LEARNING: Recalculate priority
        # Words with mistakes get MUCH higher priority (exponential)
        mistake_bonus = (stats.dont_know_count ** 1.5) * 20
        knowledge_penalty = (stats.know_count ** 0.8) * 8
        
        # If mastered (3+ correct, 0 wrong), very low priority
        if stats.know_count >= 3 and stats.dont_know_count == 0:
            knowledge_penalty += 50
        
        priority = 100.0 + mistake_bonus - knowledge_penalty
        stats.priority_score = max(1.0, priority)
        
        await session.commit()
    
    @staticmethod
    async def get_learning_stats(
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:
        """
        Get user's flashcard learning statistics.
        
        Args:
            session: Database session
            user_id: User ID
        
        Returns:
            Dictionary with learning stats
        """
        query = select(WordLearningStats).where(WordLearningStats.user_id == user_id)
        result = await session.execute(query)
        all_stats = result.scalars().all()
        
        if not all_stats:
            return {
                "total_words": 0,
                "known_words": 0,
                "learning_words": 0,
                "new_words": 0
            }
        
        # Count words by knowledge level
        known_words = sum(1 for s in all_stats if s.know_count >= 3 and s.dont_know_count == 0)
        learning_words = sum(1 for s in all_stats if s.know_count > 0 or s.dont_know_count > 0)
        learning_words -= known_words  # Exclude already known
        
        # Get total vocabulary count
        vocab_query = select(Vocabulary).where(Vocabulary.difficulty_level.in_(['A1', 'A2']))
        vocab_result = await session.execute(vocab_query)
        total_available = len(vocab_result.scalars().all())
        
        new_words = total_available - len(all_stats)
        
        return {
            "total_words": len(all_stats),
            "known_words": known_words,
            "learning_words": learning_words,
            "new_words": new_words
        }


# Singleton instance
flashcard_service = FlashcardService()
