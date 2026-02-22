import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Salt для хеширования (должен быть в .env в продакшене)
LOG_SALT = "diagnostic_bot_salt_2026"

def hash_user_id(user_id: int) -> str:
    """Хеширует user_id с солью для анонимизации"""
    salted = f"{user_id}{LOG_SALT}".encode('utf-8')
    return hashlib.sha256(salted).hexdigest()[:16]

def setup_logging():
    """Настройка основного логгера"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOGS_DIR / "bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log_session(user_id: int, language: str, pattern_label: str = None):
    """Логирование сессии (анонимизированное)"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_hash": hash_user_id(user_id),
        "language": language,
        "pattern_label": pattern_label
    }
    with open(LOGS_DIR / "sessions.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def log_verdict(user_id: int, pattern_label: str, language: str):
    """Логирование вердикта (анонимизированное, только метаданные)"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_hash": hash_user_id(user_id),
        "type": "verdict",
        "pattern_label": pattern_label,
        "language": language
    }
    with open(LOGS_DIR / "verdicts.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def log_emergency(user_id: int, code: str, trigger: str, language: str):
    """Логирование emergency (анонимизированное)"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_hash": hash_user_id(user_id),
        "type": "emergency",
        "code": code,
        "trigger_length": len(trigger),  # Только длина, не содержание
        "language": language
    }
    with open(LOGS_DIR / "emergencies.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
