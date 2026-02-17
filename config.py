import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")

SESSION_TTL = 3600
GROQ_MODEL = "llama-3.3-70b-versatile"
GOOGLE_MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.2
MAX_TOKENS = 8000  # УВЕЛИЧЕНО для RC-2
LANGUAGES = ["en", "ru", "es", "fr", "de"]
