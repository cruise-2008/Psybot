import json
import redis.asyncio as redis
from config import REDIS_URL

class RedisStorage:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
    
    async def create_session(self, user_id: int, data: dict):
        """Создание новой сессии"""
        key = f"session:{user_id}"
        await self.redis.setex(key, 3600, json.dumps(data))
    
    async def get_session(self, user_id: int) -> dict | None:
        """Получение сессии"""
        key = f"session:{user_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def update_session(self, user_id: int, data: dict):
        """Обновление сессии"""
        key = f"session:{user_id}"
        existing = await self.get_session(user_id)
        if existing:
            existing.update(data)
            await self.redis.setex(key, 3600, json.dumps(existing))
    
    async def clear_session(self, user_id: int):
        """Удаление сессии"""
        session_key = f"session:{user_id}"
        history_key = f"history:{user_id}"
        await self.redis.delete(session_key, history_key)
    
    async def add_to_history(self, user_id: int, message: dict):
        """Добавление сообщения в историю"""
        key = f"history:{user_id}"
        history = await self.get_history(user_id)
        history.append(message)
        await self.redis.setex(key, 3600, json.dumps(history))
    
    async def get_history(self, user_id: int) -> list:
        """Получение истории диалога"""
        key = f"history:{user_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else []
    
    async def increment_counter(self, counter_name: str):
        """Инкремент счётчика"""
        key = f"counter:{counter_name}"
        await self.redis.incr(key)
    
    async def get_counter(self, counter_name: str) -> int:
        """Получение значения счётчика"""
        key = f"counter:{counter_name}"
        value = await self.redis.get(key)
        return int(value) if value else 0

# Singleton instance
storage = RedisStorage()
