"""Main bot entry point."""

import asyncio
import logging
import sys
import json
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select

import config
from models.models import init_db, close_db, get_session_maker, Situation
from handlers import common, survival, review, settings, flashcard_learning, fill_blank_training, vocabulary_browser

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def load_initial_data():
    """Load initial situations data into database."""
    logger.info("Loading initial situation data...")
    
    # Load situations from JSON file
    situations_file = Path(__file__).parent / "data" / "situations.json"
    
    if not situations_file.exists():
        logger.warning("situations.json not found, skipping initial data load")
        return
    
    with open(situations_file, 'r', encoding='utf-8') as f:
        situations_data = json.load(f)
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        # Delete all existing situations to reload fresh data
        from sqlalchemy import delete, text
        
        # Ensure column exists (simple migration)
        try:
            await session.execute(text("ALTER TABLE situations ADD COLUMN IF NOT EXISTS vocabulary_focus JSON"))
            await session.commit()
        except Exception as e:
            logger.warning(f"Migration warning: {e}")
            
        await session.execute(delete(Situation))
        
        # Add all situations from JSON
        for situation_data in situations_data:
            situation = Situation(
                title=situation_data['title'],
                description=situation_data['description'],
                level=situation_data['level'],
                context_prompt=situation_data['context_prompt'],
                is_active=situation_data.get('is_active', True),
                vocabulary_focus=situation_data.get('vocabulary_focus', [])
            )
            session.add(situation)
        
        await session.commit()
        logger.info(f"✅ Loaded {len(situations_data)} situations")


async def load_initial_words():
    """Load initial vocabulary words into database."""
    logger.info("Loading initial vocabulary words...")
    
    # Load words from JSON file
    words_file = Path(__file__).parent / "data" / "initial_words.json"
    
    if not words_file.exists():
        logger.warning("initial_words.json not found, skipping initial words load")
        return
    
    with open(words_file, 'r', encoding='utf-8') as f:
        words_data = json.load(f)
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        from models.models import Vocabulary
        from sqlalchemy import text
        
        # Ensure new column exists (simple migration)
        try:
            await session.execute(text("ALTER TABLE vocabulary ADD COLUMN IF NOT EXISTS example_sentence_pl TEXT"))
            await session.commit()
        except Exception as e:
            logger.warning(f"Migration warning: {e}")
        
        # Add words if they don't exist
        added_count = 0
        for word_data in words_data:
            # Check if word already exists
            existing = await session.execute(
                select(Vocabulary).where(Vocabulary.word_polish == word_data['word_polish'])
            )
            if existing.scalar_one_or_none():
                continue
            
            word = Vocabulary(
                word_polish=word_data['word_polish'],
                translation_ua=word_data['translation_ua'],
                translation_ru=word_data['translation_ru'],
                example_sentence_pl=word_data.get('example_sentence_pl'),
                emoji=word_data.get('emoji'),
                category=word_data.get('category', 'general'),
                difficulty_level=word_data.get('difficulty_level', 'A1')
            )
            session.add(word)
            added_count += 1
        
        await session.commit()
        logger.info(f"✅ Loaded {added_count} new vocabulary words")



async def main():
    """Main bot function."""
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Create data directory for SQLite database
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Data directory ready: {data_dir}")
    
    # Initialize database
    await init_db()
    
    # Load initial data
    await load_initial_data()
    
    # Load initial vocabulary words
    await load_initial_words()

    
    # Initialize bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register routers
    dp.include_router(common.router)
    dp.include_router(flashcard_learning.router)
    dp.include_router(fill_blank_training.router)
    dp.include_router(vocabulary_browser.router)
    dp.include_router(survival.router)
    dp.include_router(review.router)
    dp.include_router(settings.router)
    
    logger.info("🤖 Bot started successfully!")
    logger.info(f"📊 Level: {config.LOG_LEVEL}")
    logger.info(f"🗄️ Database: {config.DATABASE_URL}")
    
    try:
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        await bot.session.close()
        await close_db()
        logger.info("👋 Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
