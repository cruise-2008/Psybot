import json
import logging
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def get_response(self, prompt: str, user_id: int = None):
        try:
            # Превращаем строку или список в правильный формат для Gemini (parts вместо content)
            formatted_prompt = [{"role": "user", "parts": [prompt]}]
            
            response = await self.model.generate_content_async(formatted_prompt)
            text = response.text.strip()
            
            # Очистка от markdown
            text = re.sub(r'```json\s*|```', '', text)
            
            try:
                data = json.loads(text)
                return data if data else {}
            except json.JSONDecodeError:
                type_match = re.search(r'"type"\s*:\s*"(.*?)"', text)
                content_match = re.search(r'"content"\s*:\s*"(.*)"', text, re.DOTALL)
                if type_match and content_match:
                    return {
                        "type": type_match.group(1),
                        "content": content_match.group(1).replace('\\"', "'").replace('"', "'")
                    }
                return {}
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return {} # Возвращаем пустой дикт вместо None, чтобы избежать ошибок .get()

llm_client = LLMClient()
