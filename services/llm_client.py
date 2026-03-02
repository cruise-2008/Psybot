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

    async def get_response(self, prompt: str):
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Извлекаем контент между кавычками поля "content"
                match = re.search(r'"content"\s*:\s*"(.*)"\s*\}', text, re.DOTALL)
                if match:
                    clean_content = match.group(1).replace('"', "'")
                    return {"type": "RC-2", "content": clean_content}
                return None
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None

llm_client = LLMClient()
