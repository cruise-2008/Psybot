import json
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
        import re
        system_message = f"""{self.system_prompt}

User's language: {user_language}. Respond in this language.

CRITICAL JSON RULES:
1. Output ONLY valid JSON
2. NO markdown fences
3. ALL strings must use double quotes, not single quotes
4. Escape ALL quotes inside strings: use \\" not "
5. Example WRONG: "Say \"I am okay\" to yourself"
6. Example RIGHT: "Say \\\"I am okay\\\" to yourself"
7. Keep text concise to avoid truncation
8. Test your JSON mentally before responding"""
        
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

        # Fix apostrophes (English + French)
        # English: I"m -> I'm, people"s -> people's
        content = re.sub(r'(\w)"(s|m|t|re|ve|ll|d)\b', r"\1'\2", content)
        # French: qu"il -> qu'il, d"une -> d'une
        content = re.sub(r'\b([JjDdLlQqMmTtSsNnCc])"(\w)', r"\1'\2", content)
        
        # Фикс незакрытых кавычек в испанском/французском
        # Заменить " внутри строк на \"
        # Паттерн: "text "word" text" → "text \"word\" text"
        def fix_quotes(match):
            s = match.group(1)
            # Заменить все внутренние " на \"
            s_fixed = s.replace('"', '\\"')
            return f'"{s_fixed}"'
        
        # НЕ трогать экранированные "
        # content = re.sub(r'"([^"]*)"', fix_quotes, content)
        
        if not content.endswith("}"):
            logger.warning("Response appears truncated")
            last_brace = content.rfind("}")
            if last_brace > 0:
                content = content[:last_brace+1]
        
        content = content.replace("'", '"')
        
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
