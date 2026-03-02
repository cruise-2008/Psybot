import json
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def get_response(self, prompt: str):
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text
            
            # Очистка текста от возможных артефактов markdown
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            
            # Пытаемся распарсить JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Если упало из-за внутренних кавычек, пробуем жесткую очистку
                import re
                # Ищем содержимое между "content":" и "}
                content_match = re.search(r'"content":"(.*)"}', text, re.DOTALL)
                if content_match:
                    return {"type": "RC-2", "content": content_match.group(1).replace('"', "'")}
                raise
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None
