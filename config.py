import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///data/database.db')

# SRS Algorithm Parameters
SRS_MIN_EASINESS = float(os.getenv('SRS_MIN_EASINESS', '1.3'))
SRS_INITIAL_INTERVAL = int(os.getenv('SRS_INITIAL_INTERVAL', '1'))
SRS_GRADUATION_INTERVAL = int(os.getenv('SRS_GRADUATION_INTERVAL', '6'))

# Review Settings
MAX_REVIEWS_PER_SESSION = 10
REVIEW_CHECK_INTERVAL = 3600  # Check every hour (in seconds)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Difficulty Scaling
DIFFICULTY_THRESHOLD = 5  # After 5 correct answers, increase difficulty

# TTS Configuration
TTS_MODEL = "tts-1"
TTS_VOICE = "alloy"
TTS_AUDIO_DIR = "audio"

# AI Model Configuration
GROQ_MODEL = "mixtral-8x7b-32768"  # Good for structured output
GROQ_TEMPERATURE = 0.7
GROQ_MAX_TOKENS = 1000

# Validate required environment variables
def validate_config():
    """Validate that all required environment variables are set."""
    required_vars = {
        'BOT_TOKEN': BOT_TOKEN,
        'GROQ_API_KEY': GROQ_API_KEY,
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please create a .env file based on .env.example"
        )
    
    return True
