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
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Очистка от markdown оберток
            text = re.sub(r'```json\s*|```', '', text)
            
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Резервный парсинг для сложных случаев с кавычками
                type_match = re.search(r'"type"\s*:\s*"(.*?)"', text)
                content_match = re.search(r'"content"\s*:\s*"(.*)"', text, re.DOTALL)
                
                if type_match and content_match:
                    return {
                        "type": type_match.group(1),
                        "content": content_match.group(1).replace('\\"', "'").replace('"', "'")
                    }
                logger.error(f"Failed to parse LLM response: {text}")
                return None
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None

llm_client = LLMClient()
