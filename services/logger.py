import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
import os

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Generate or load encryption key
KEY_FILE = LOGS_DIR / ".log_key"
if KEY_FILE.exists():
    with open(KEY_FILE, "rb") as f:
        ENCRYPTION_KEY = f.read()
else:
    ENCRYPTION_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(ENCRYPTION_KEY)
    os.chmod(KEY_FILE, 0o600)  # Read/write for owner only

cipher = Fernet(ENCRYPTION_KEY)

# Salt for hashing (change this to random value in production)
SALT = os.getenv("LOG_SALT", "psybot_salt_2026").encode()

def hash_user_id(user_id: int) -> str:
    """Convert user_id to salted hash for anonymization"""
    data = f"{user_id}".encode() + SALT
    return hashlib.sha256(data).hexdigest()[:16]

def encrypt_log_entry(log_entry: dict) -> str:
    """Encrypt log entry"""
    json_str = json.dumps(log_entry, ensure_ascii=False)
    encrypted = cipher.encrypt(json_str.encode())
    return encrypted.decode()

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOGS_DIR / "bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log_verdict(user_id: int, pattern_label: str, language: str):
    """Log verdict with hashed user_id and encrypted data"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id_hash": hash_user_id(user_id),
        "type": "verdict",
        "pattern_label": pattern_label,
        "language": language
    }
    encrypted_entry = encrypt_log_entry(log_entry)
    with open(LOGS_DIR / "verdicts.jsonl", "a", encoding='utf-8') as f:
        f.write(encrypted_entry + "\n")

def log_emergency(user_id: int, code: str, trigger: str, language: str):
    """Log emergency with hashed user_id and encrypted data"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id_hash": hash_user_id(user_id),
        "type": "emergency",
        "code": code,
        "trigger": trigger[:100],  # Truncate trigger to avoid PII
        "language": language
    }
    encrypted_entry = encrypt_log_entry(log_entry)
    with open(LOGS_DIR / "emergencies.jsonl", "a", encoding='utf-8') as f:
        f.write(encrypted_entry + "\n")
