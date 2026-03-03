import json
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def get_response(self, prompt: str, user_id: int = None):
        try:
            # Твой оригинальный вызов
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Минимальная очистка markdown, если Gemini его добавит
            if text.startswith("```json"):
                text = text.split("```json")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return {}

llm_client = LLMClient()
