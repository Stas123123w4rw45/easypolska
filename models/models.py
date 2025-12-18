from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import config

Base = declarative_base()


class User(Base):
    """User model for storing user information and progress."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    level = Column(String(10), default='A1')  # A1, A2, B1
    streak_days = Column(Integer, default=0)
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    progress = relationship('UserProgress', back_populates='user', cascade='all, delete-orphan')
    quiz_history = relationship('UserQuizHistory', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, level={self.level})>"


class Vocabulary(Base):
    """Vocabulary model for Polish words."""
    __tablename__ = 'vocabulary'
    
    id = Column(Integer, primary_key=True)
    word_polish = Column(String(255), nullable=False, unique=True, index=True)
    translation_ua = Column(String(255), nullable=False)
    translation_ru = Column(String(255), nullable=False)
    context_sentence = Column(Text, nullable=True)
    example_sentence_pl = Column(Text, nullable=True)  # Example sentence in Polish for flashcards
    difficulty_level = Column(String(10), default='A1')  # A1, A2, B1
    category = Column(String(100), nullable=True)  # e.g., "food", "transport"
    
    # Relationships
    user_progress = relationship('UserProgress', back_populates='word', cascade='all, delete-orphan')
    learning_stats = relationship('WordLearningStats', back_populates='word', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Vocabulary(word={self.word_polish}, level={self.difficulty_level})>"


class UserProgress(Base):
    """User progress for vocabulary using SRS algorithm."""
    __tablename__ = 'user_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('vocabulary.id'), nullable=False)
    
    # SRS Parameters
    srs_stage = Column(Integer, default=0)  # 0-5
    next_review_time = Column(DateTime, default=func.now())
    last_quality = Column(Integer, default=0)  # 0-5 (SuperMemo-2 quality)
    repetitions = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=0)
    
    # Metadata
    last_reviewed = Column(DateTime, nullable=True)
    times_reviewed = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    times_wrong = Column(Integer, default=0)
    
    # Relationships
    user = relationship('User', back_populates='progress')
    word = relationship('Vocabulary', back_populates='user_progress')
    
    def __repr__(self):
        return f"<UserProgress(user_id={self.user_id}, word_id={self.word_id}, stage={self.srs_stage})>"


class Situation(Base):
    """Pre-defined learning situations/scenarios."""
    __tablename__ = 'situations'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    level = Column(String(10), default='A1')
    context_prompt = Column(Text, nullable=False)  # Prompt sent to AI
    is_active = Column(Boolean, default=True)
    vocabulary_focus = Column(JSON, nullable=True)  # List of target words
    
    # Relationships
    quiz_history = relationship('UserQuizHistory', back_populates='situation')
    
    def __repr__(self):
        return f"<Situation(title={self.title}, level={self.level})>"


class UserQuizHistory(Base):
    """Track user quiz attempts for analytics."""
    __tablename__ = 'user_quiz_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    situation_id = Column(Integer, ForeignKey('situations.id'), nullable=True)
    word_id = Column(Integer, ForeignKey('vocabulary.id'), nullable=True)
    
    question = Column(Text, nullable=False)
    user_answer = Column(String(500), nullable=True)
    correct_answer = Column(String(500), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship('User', back_populates='quiz_history')
    situation = relationship('Situation', back_populates='quiz_history')
    
    def __repr__(self):
        return f"<UserQuizHistory(user_id={self.user_id}, is_correct={self.is_correct})>"


class WordLearningStats(Base):
    """Track flashcard learning statistics for words."""
    __tablename__ = 'word_learning_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('vocabulary.id'), nullable=False)
    
    # Statistics
    know_count = Column(Integer, default=0)  # Green button presses
    dont_know_count = Column(Integer, default=0)  # Red button presses
    last_shown = Column(DateTime, nullable=True)  # Last time shown to user
    priority_score = Column(Float, default=100.0)  # Priority for showing (higher = more urgent)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    word = relationship('Vocabulary', back_populates='learning_stats')
    
    def __repr__(self):
        return f"<WordLearningStats(user_id={self.user_id}, word_id={self.word_id}, priority={self.priority_score})>"


# Database engine and session management
engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection and create tables."""
    global engine, async_session_maker
    
    engine = create_async_engine(
        config.DATABASE_URL,
        echo=False,
        future=True
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database initialized successfully")


def get_session_maker():
    """Get the session maker (must be called after init_db)."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_session_maker


async def get_session() -> AsyncSession:
    """Get database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_maker() as session:
        yield session


async def close_db():
    """Close database connection."""
    global engine
    if engine:
        await engine.dispose()
        print("✅ Database connection closed")
