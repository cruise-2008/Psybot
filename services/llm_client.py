import json
import re
import logging
from config import LLM_PROVIDER, GROQ_API_KEY, GOOGLE_API_KEY, GROQ_MODEL, TEMPERATURE, MAX_TOKENS

logger = logging.getLogger(__name__)

RATE_LIMIT_MESSAGES = {
    "ru": "Временная перегрузка сервиса. Попробуйте через 1 час.",
    "en": "Temporary service overload. Try again in 1 hour.",
    "es": "Sobrecarga temporal del servicio. Intente nuevamente en 1 hora.",
    "fr": "Surcharge temporaire du service. Réessayez dans 1 heure.",
    "de": "Temporäre Dienstüberlastung. Versuchen Sie es in 1 Stunde erneut."
}

class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        if self.provider == "groq":
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)
            self.model = GROQ_MODEL
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            self.client = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_TOKENS
                }
            )
            self.model = "gemini-2.5-flash"
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def get_response(self, conversation_history: list, user_language: str) -> dict:
        try:
            if self.provider == "groq":
                return await self._get_groq_response(conversation_history, user_language)
            elif self.provider == "google":
                return await self._get_google_response(conversation_history, user_language)
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                logger.error(f"LLM API rate limit exceeded: {e}")
                return {
                    "type": "RATE_LIMIT_ERROR",
                    "message": RATE_LIMIT_MESSAGES.get(user_language, RATE_LIMIT_MESSAGES["en"])
                }
            logger.error(f"LLM API error: {e}")
            raise

    async def _get_groq_response(self, conversation_history: list, user_language: str) -> dict:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"User's language: {user_language}. Respond in this language."},
            *conversation_history
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        logger.info(f"Groq response type: {parsed.get('type')}")
        return parsed

    async def _get_google_response(self, conversation_history: list, user_language: str) -> dict:
        system_message = f"""{self.system_prompt}

User's language: {user_language}. Respond in this language.

CRITICAL JSON RULE:
Inside field values, ALWAYS use single quotes ' for any quoted text, NEVER double quotes "
Example CORRECT: "When you say 'I must accept'"
Example WRONG: "When you say \\"I must accept\\""
NO markdown fences
Keep text concise"""

        history_text = ""
        for msg in conversation_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n\n"

        full_prompt = f"{system_message}\n\n{history_text}Assistant:"

        response = self.client.generate_content(full_prompt)
        content = response.text.strip()

        logger.debug(f"Raw Google response length: {len(content)}")

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        if not content.endswith("}"):
            logger.warning("Response appears truncated")
            last_brace = content.rfind("}")
            if last_brace > 0:
                content = content[:last_brace+1]

        # Handle case where LLM returns two JSONs
        if content.count('}{') > 0:
            logger.warning("LLM returned multiple JSONs, taking first one")
            first_json_end = content.find('}{') + 1
            content = content[:first_json_end]
        
        # Handle case where LLM returns two JSONs
        if content.count('}{') > 0:
            logger.warning("LLM returned multiple JSONs, taking first one")
            first_json_end = content.find('}{') + 1
            content = content[:first_json_end]
        
        # Handle case where LLM returns two JSONs
        if content.count('}{') > 0:
            logger.warning("LLM returned multiple JSONs, taking first one")
            first_json_end = content.find('}{') + 1
            content = content[:first_json_end]
        
        # Fix single quotes in JSON keys (LLM sometimes uses ' instead of ")
        content = re.sub(r"'(type|question|options|content|emergency_code|detected_trigger|user_language)':", r'"":', content)
        
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error at position {e.pos}")
            logger.error(f"Problematic content around error: {content[max(0, e.pos-50):e.pos+50]}")
            logger.error(f"Full content: {content}")
            return {
                "type": "ERROR",
                "message": "Не удалось обработать ответ. Попробуйте снова."
            }

        logger.info(f"Google response type: {parsed.get('type')}")
        return parsed

llm_client = LLMClient()
