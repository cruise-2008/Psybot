import json
import logging
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# Локализованные сообщения о rate limit
RATE_LIMIT_MESSAGES = {
    "ru": "Временная перегрузка сервиса. Попробуйте через 40 минут.",
    "en": "Temporary service overload. Try again in 40 minutes.",
    "es": "Sobrecarga temporal del servicio. Intente nuevamente en 40 minutos.",
    "fr": "Surcharge temporaire du service. Réessayez dans 40 minutes.",
    "de": "Temporäre Dienstüberlastung. Versuchen Sie es in 40 Minuten erneut."
}

class GroqDiagnosticClient:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
        
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
    
    async def get_response(self, conversation_history: list, user_language: str) -> dict:
        """Отправка запроса в Groq API"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"User's language: {user_language}. Respond in this language."},
            *conversation_history
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            logger.info(f"Groq response type: {parsed.get('type')}")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw content: {content}")
            raise
        except Exception as e:
            error_msg = str(e)
            
            # Проверка на rate limit
            if "rate_limit_exceeded" in error_msg or "429" in error_msg:
                logger.error(f"Groq API rate limit exceeded: {e}")
                return {
                    "type": "RATE_LIMIT_ERROR",
                    "message": RATE_LIMIT_MESSAGES.get(user_language, RATE_LIMIT_MESSAGES["en"])
                }
            
            logger.error(f"Groq API error: {e}")
            raise

# Singleton instance
groq_client = GroqDiagnosticClient()
