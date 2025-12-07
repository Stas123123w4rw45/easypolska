#!/bin/bash
# Setup script for EasyPolska bot

echo "🚀 Setting up EasyPolska Bot..."

# Create .env file from template with provided keys
cat > .env << 'EOF'
# Environment variables
# IMPORTANT: This file contains actual API keys. Never commit to Git!

# Telegram Bot API Token
BOT_TOKEN=your_telegram_bot_token_here

# Groq API Key
GROQ_API_KEY=your_groq_api_key_here

# OpenAI API Key (for TTS) - Add your key if you want audio pronunciation
OPENAI_API_KEY=

# Database URL (SQLite default)
DATABASE_URL=sqlite+aiosqlite:///data/database.db

# SRS Algorithm Parameters
SRS_MIN_EASINESS=1.3
SRS_INITIAL_INTERVAL=1
SRS_GRADUATION_INTERVAL=6

# Logging Level
LOG_LEVEL=INFO
EOF

echo "✅ Created .env file with API keys"

# Create data directory for database
mkdir -p data
echo "✅ Created data directory"

# Create audio directory for TTS files
mkdir -p audio
echo "✅ Created audio directory"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Run the bot: python bot.py"
echo ""
echo "Note: If you have an OpenAI API key for TTS, add it to .env"
