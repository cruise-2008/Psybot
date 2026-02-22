import logging
import json
from datetime import datetime
from pathlib import Path

# Создание директории для логов
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

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
    """Логирование сессии в sessions.jsonl"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "language": language,
        "pattern_label": pattern_label
    }
    with open(LOGS_DIR / "sessions.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def log_verdict(user_id: int, pattern_label: str, language: str):
    return  # Disabled for EU compliance
    """
    """Логирование вердикта в verdicts.jsonl"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "type": "verdict",
        "pattern_label": pattern_label,
        "language": language
    }
    """
    with open(LOGS_DIR / "verdicts.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def log_emergency(user_id: int, code: str, trigger: str, language: str):
    """Логирование emergency в emergencies.jsonl"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "type": "emergency",
        "code": code,
        "trigger": trigger,
        "language": language
    }
    with open(LOGS_DIR / "emergencies.jsonl", "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
