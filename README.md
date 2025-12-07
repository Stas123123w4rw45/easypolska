# EasyPolska - Polish Learning Telegram Bot 🇵🇱

A comprehensive Telegram bot for learning Polish, specifically designed for Ukrainian and Russian speakers. Features AI-powered quizzes with linguistically-targeted content and a spaced repetition system (SRS) for vocabulary retention.

## 🌟 Features

- **🎯 Survival Mode**: Learn through real-life scenarios (shopping, restaurant, transport, etc.)
- **🤖 AI-Powered Quizzes**: Questions with distractors based on common Slavic speaker mistakes
- **📚 Spaced Repetition System**: SuperMemo-2 algorithm for optimal vocabulary retention
- **🔊 Audio Pronunciation**: Polish text-to-speech for authentic pronunciation
- **📊 Progress Tracking**: Monitor your streak, vocabulary size, and mastery levels
- **🎚️ Adaptive Difficulty**: Automatically adjusts based on your performance

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Framework**: Aiogram 3.x (Async)
- **Database**: SQLite (MVP) / PostgreSQL ready
- **AI Engine**: Groq API (mixtral-8x7b-32768)
- **TTS**: OpenAI TTS API

## 📋 Requirements

- Python 3.11 or higher
- Telegram Bot Token
- Groq API Key
- OpenAI API Key (optional, for TTS)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Stas123123w4rw45/easypolska.git
cd easypolska
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional for TTS
```

### 5. Run the bot

```bash
python bot.py
```

## 📁 Project Structure

```
easypolska/
├── bot.py                 # Main entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── models/
│   └── models.py         # SQLAlchemy database models
├── services/
│   ├── ai_service.py     # Groq AI integration
│   ├── srs_service.py    # SuperMemo-2 algorithm
│   └── tts_service.py    # OpenAI TTS integration
├── handlers/
│   ├── common.py         # /start, /help, /stats commands
│   ├── survival.py       # Survival mode handlers
│   ├── review.py         # SRS review handlers
│   └── settings.py       # Settings & progress handlers
├── utils/
│   ├── states.py         # FSM states
│   ├── keyboards.py      # Inline keyboards
│   └── prompts.py        # AI system prompts
└── data/
    └── situations.json   # Pre-defined scenarios
```

## 🎮 Usage

### Bot Commands

- `/start` - Start the bot and show main menu
- `/help` - Display help information
- `/stats` - View your learning statistics
- `/menu` - Return to main menu

### Main Features

#### 🎯 Survival Mode
Learn Polish through real-life scenarios:
- 🛒 At Żabka (Shopping)
- 🚗 Ordering Uber
- 🍽️ At the Restaurant
- 📮 At the Post Office
- 🚂 Buying Train Tickets
- 🏥 At the Doctor's
- 🏠 Renting an Apartment

Each scenario includes:
- Context introduction with audio
- AI-generated quiz with Slavic-focused distractors
- Detailed grammatical explanations

#### 📚 SRS Review
Smart vocabulary review system:
- Fill-in-the-blank questions (not direct translation)
- Adaptive review intervals
- Quality-based scheduling (0-5 scale)
- Progress tracking per word

#### 📊 Progress Tracking
Monitor your learning:
- Current level (A1/A2/B1)
- Learning streak in days
- Vocabulary statistics (total, due, mastered, learning, new)

## 🧠 How It Works

### AI-Powered Quiz Generation

The bot uses specially crafted system prompts to generate quizzes that target common mistakes made by Ukrainian/Russian speakers:

- **False Friends**: Words that look similar but have different meanings
- **Case Confusion**: Especially Instrumental, Locative, Genitive
- **Preposition Errors**: w/na, do/na, z/od confusion
- **Aspect Mistakes**: Perfective vs imperfective verbs
- **Gender Agreement**: Wrong noun-adjective agreement

### SuperMemo-2 SRS Algorithm

The spaced repetition system uses the proven SuperMemo-2 algorithm:

1. **Quality Assessment** (0-5):
   - 5 = Perfect recall
   - 4 = Correct with hesitation
   - 3 = Correct with difficulty
   - 2 = Incorrect but recalled after seeing answer
   - 1 = Incorrect but familiar
   - 0 = Complete blackout

2. **Interval Calculation**:
   - First review: 1 day
   - Second review: 6 days
   - Subsequent reviews: Previous interval × Easiness Factor
   - Failed reviews: Reset to 0

3. **Adaptive Learning**: Intervals adjust based on your performance

## 🔧 Configuration

### Database

By default, the bot uses SQLite for simplicity. To use PostgreSQL:

1. Install PostgreSQL driver:
```bash
pip install asyncpg
```

2. Update `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/easypolska
```

### SRS Parameters

Adjust in `.env`:
```
SRS_MIN_EASINESS=1.3
SRS_INITIAL_INTERVAL=1
SRS_GRADUATION_INTERVAL=6
```

### AI Model

Default: `mixtral-8x7b-32768` (Groq)

To change, edit `config.py`:
```python
GROQ_MODEL = "your-model-name"
```

## 📝 Adding New Scenarios

Edit `data/situations.json`:

```json
{
  "title": "Your Scenario Title",
  "description": "Detailed description",
  "level": "A1",
  "context_prompt": "Context for AI generation",
  "is_active": true
}
```

The bot will automatically load scenarios on startup.

## 🐛 Troubleshooting

### Bot doesn't start
- Check that all API keys in `.env` are correct
- Ensure Python 3.11+ is installed
- Verify all dependencies are installed

### No audio pronunciation
- Ensure `OPENAI_API_KEY` is set in `.env`
- Check OpenAI API credits
- TTS is optional; bot works without it

### Database errors
- Delete `data/database.db` and restart bot
- Check file permissions in `data/` directory

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📄 License

MIT License - feel free to use this project for your own learning!

## 📧 Support

For questions or issues, please open an issue on GitHub.

---

Made with ❤️ for Polish language learners
