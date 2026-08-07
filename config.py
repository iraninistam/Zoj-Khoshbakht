import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# AI Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# AI Models
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat"
)

CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-3-5-sonnet-latest"
)

# Owner
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Match settings
NUM_QUESTIONS = int(
    os.getenv("NUM_QUESTIONS", "6")
)

# Runtime
PORT = int(
    os.getenv("PORT", "10000")
)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if WEBHOOK_URL:
    WEBHOOK_URL = WEBHOOK_URL.rstrip("/")