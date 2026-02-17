from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import logging
logger = logging.getLogger(__name__)

from services.llm_client import llm_client
from services.redis_storage import storage
from services.logger import log_verdict

router = Router()

class DiagnosticStates(StatesGroup):
    s1 = State()
    s2 = State()
    s3 = State()
    decision_point = State()
    s4 = State()
    s5 = State()
    s6 = State()

ERROR_MESSAGES = {
    "ru": "Произошла ошибка. Попробуйте /start",
    "en": "An error occurred. Try /start",
    "es": "Ocurrió un error. Intente /start",
    "fr": "Une erreur s'est produite. Essayez /start",
    "de": "Ein Fehler ist aufgetreten. Versuchen Sie /start"
}

SESSION_ENDED_MESSAGES = {
    "ru": "Сессия завершена. Используйте /start для новой консультации.",
    "en": "Session ended. Use /start for a new consultation.",
    "es": "Sesión finalizada. Use /start para una nueva consulta.",
    "fr": "Session terminée. Utilisez /start pour une nouvelle consultation.",
    "de": "Sitzung beendet. Verwenden Sie /start für eine neue Beratung."
}

def format_question_with_options(question: str, options: list, question_num: int, total: int = 3, language: str = "ru") -> str:
    prompts = {
        "ru": f"💬 Напишите номер (1-{len(options)}) и/или свой ответ:",
        "en": f"💬 Write number (1-{len(options)}) or your answer:",
        "es": f"💬 Escriba el número (1-{len(options)}) o su respuesta:",
        "fr": f"💬 Écrivez le numéro (1-{len(options)}) ou votre réponse:",
        "de": f"💬 Schreiben Sie die Nummer (1-{len(options)}) oder Ihre Antwort:"
    }
    
    question_labels = {
        "ru": f"Вопрос {question_num}/{total}:",
        "en": f"Question {question_num}/{total}:",
        "es": f"Pregunta {question_num}/{total}:",
        "fr": f"Question {question_num}/{total}:",
        "de": f"Frage {question_num}/{total}:"
    }
    
    formatted_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    prompt = prompts.get(language, prompts["en"])
    
    if question_num == 0:
        return f"{question}\n\n{formatted_options}\n\n{prompt}"
    
    label = question_labels.get(language, question_labels["en"])
    return f"{label}\n{question}\n\n{formatted_options}\n\n{prompt}"

def map_input_to_option(user_input: str, options: list) -> str:
    user_input = user_input.strip()
    
    if user_input and user_input[0].isdigit():
        idx = int(user_input[0]) - 1
        if 0 <= idx < len(options):
            if len(user_input) == 1:
                return options[idx]
            elif len(user_input) > 1 and user_input[1] == ' ':
                additional_text = user_input[2:].strip()
                return f"{options[idx]}. {additional_text}"
    
    return user_input

async def start_diagnostic(message: Message, state: FSMContext, s0_text: str):
    user_id = message.from_user.id
    
    try:
        session = await storage.get_session(user_id)
        if not session:
            await message.answer("Сессия истекла. Используйте /start")
            return
        
        lang = session.get("language", "en")
        
        await storage.add_to_history(user_id, {"role": "user", "content": s0_text})
        
        llm_response = await llm_client.get_response(
            await storage.get_history(user_id),
            lang
        )
        
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        
        await storage.add_to_history(user_id, {
            "role": "assistant", 
            "content": llm_response["question"]
        })
        await storage.update_session(user_id, {"last_response": llm_response})
        
        question_text = format_question_with_options(
            llm_response["question"],
            llm_response["options"],
            question_num=1,
            language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s1)
        
        logger.info(f"User {user_id} started diagnostic with S1")
        
    except Exception as e:
        logger.error(f"Error in start_diagnostic: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

@router.message(DiagnosticStates.s1)
async def handle_s1(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        session = await storage.get_session(user_id)
        if not session:
            await message.answer("Сессия истекла. Используйте /start")
            return
        
        lang = session.get("language", "en")
        last_response = session.get("last_response", {})
        options = last_response.get("options", [])
        
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        
        llm_response = await llm_client.get_response(
            await storage.get_history(user_id),
            lang
        )
        
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        
        await storage.add_to_history(user_id, {
            "role": "assistant",
            "content": llm_response["question"]
        })
        await storage.update_session(user_id, {"last_response": llm_response})
        
        question_text = format_question_with_options(
            llm_response["question"],
            llm_response["options"],
            question_num=2,
            language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s2)
        
    except Exception as e:
        logger.error(f"Error in handle_s1: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

@router.message(DiagnosticStates.s2)
async def handle_s2(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        last_response = session.get("last_response", {})
        options = last_response.get("options", [])
        
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        
        llm_response = await llm_client.get_response(
            await storage.get_history(user_id),
            lang
        )
        
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        
        await storage.add_to_history(user_id, {
            "role": "assistant",
            "content": llm_response["question"]
        })
        await storage.update_session(user_id, {"last_response": llm_response})
        
        question_text = format_question_with_options(
            llm_response["question"],
            llm_response["options"],
            question_num=3,
            language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s3)
        
    except Exception as e:
        logger.error(f"Error in handle_s2: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

@router.message(DiagnosticStates.s3)
async def handle_s3(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        last_response = session.get("last_response", {})
        options = last_response.get("options", [])
        
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        
        decision_request = "Now provide ONLY the decision point with exactly 2 options: deep analysis or show result."
        await storage.add_to_history(user_id, {"role": "user", "content": decision_request})
        
        llm_response = await llm_client.get_response(
            await storage.get_history(user_id),
            lang
        )
        
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        
        if len(llm_response.get("options", [])) != 2:
            logger.warning(f"LLM skipped decision point, forcing it manually for user {user_id}")
            
            decision_options_map = {
                "ru": ["Глубокий анализ (3 дополнительных вопроса)", "Показать результат сейчас"],
                "en": ["Deep analysis (3 additional questions)", "Show result now"],
                "es": ["Análisis profundo (3 preguntas adicionales)", "Mostrar resultado ahora"],
                "fr": ["Analyse approfondie (3 questions supplémentaires)", "Afficher le résultat maintenant"],
                "de": ["Tiefenanalyse (3 zusätzliche Fragen)", "Ergebnis jetzt anzeigen"]
            }
            
            decision_question_map = {
                "ru": "Анализ завершен.",
                "en": "Analysis complete.",
                "es": "Análisis completo.",
                "fr": "Analyse terminée.",
                "de": "Analyse abgeschlossen."
            }
            
            llm_response = {
                "type": "RC-1",
                "question": decision_question_map.get(lang, decision_question_map["en"]),
                "options": decision_options_map.get(lang, decision_options_map["en"])
            }
        
        await storage.add_to_history(user_id, {
            "role": "assistant",
            "content": llm_response["question"]
        })
        await storage.update_session(user_id, {"last_response": llm_response})
        
        question_text = format_question_with_options(
            llm_response["question"],
            llm_response["options"],
            question_num=0,
            language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.decision_point)
        
    except Exception as e:
        logger.error(f"Error in handle_s3: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

@router.message(DiagnosticStates.decision_point)
async def handle_decision(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text.strip() not in ["1", "2"]:
        return
    
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        last_response = session.get("last_response", {})
        options = last_response.get("options", [])
        
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        
        if "1" in message.text or "deep" in user_answer.lower() or "глубок" in user_answer.lower() or "profundo" in user_answer.lower() or "approfondie" in user_answer.lower() or "tiefenanalyse" in user_answer.lower():
            llm_response = await llm_client.get_response(
                await storage.get_history(user_id),
                lang
            )
            
            if llm_response.get("type") == "RATE_LIMIT_ERROR":
                await message.answer(llm_response["message"])
                await storage.clear_session(user_id)
                await state.clear()
                return
            
            if llm_response.get("type") == "RC-3":
                from handlers.emergency import handle_emergency
                await handle_emergency(message, state, llm_response)
                return
            
            await storage.add_to_history(user_id, {
                "role": "assistant",
                "content": llm_response["question"]
            })
            await storage.update_session(user_id, {"last_response": llm_response})
            
            question_text = format_question_with_options(
                llm_response["question"],
                llm_response["options"],
                question_num=4,
                total=6,
                language=lang
            )
            await message.answer(question_text)
            await state.set_state(DiagnosticStates.s4)
        else:
            llm_response = await llm_client.get_response(
                await storage.get_history(user_id),
                lang
            )
            
            if llm_response.get("type") == "RATE_LIMIT_ERROR":
                await message.answer(llm_response["message"])
                await storage.clear_session(user_id)
                await state.clear()
                return
            
            if llm_response.get("type") == "RC-3":
                from handlers.emergency import handle_emergency
                await handle_emergency(message, state, llm_response)
                return
            
            if llm_response.get("type") == "RC-2":
                await send_verdict(message, state, llm_response, user_id, lang)
            
    except Exception as e:
        logger.error(f"Error in handle_decision: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

@router.message(DiagnosticStates.s4)
@router.message(DiagnosticStates.s5)
@router.message(DiagnosticStates.s6)
async def handle_deep_analysis(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    state_map = {
        "DiagnosticStates:s4": (4, DiagnosticStates.s5),
        "DiagnosticStates:s5": (5, DiagnosticStates.s6),
        "DiagnosticStates:s6": (6, None)
    }
    
    question_num, next_state = state_map.get(current_state, (4, None))
    
    logger.info(f"Deep analysis: user {user_id}, current_state={current_state}, question_num={question_num}, next_state={next_state}")
    
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        last_response = session.get("last_response", {})
        options = last_response.get("options", [])
        
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        
        llm_response = await llm_client.get_response(
            await storage.get_history(user_id),
            lang
        )
        
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        
        await storage.add_to_history(user_id, {
            "role": "assistant",
            "content": llm_response.get("question", "")
        })
        await storage.update_session(user_id, {"last_response": llm_response})
        
        if next_state is None or llm_response.get("type") == "RC-2":
            await send_verdict(message, state, llm_response, user_id, lang)
        else:
            question_text = format_question_with_options(
                llm_response["question"],
                llm_response["options"],
                question_num=question_num + 1,
                total=6,
                language=lang
            )
            await message.answer(question_text)
            await state.set_state(next_state)
        
    except Exception as e:
        logger.error(f"Error in handle_deep_analysis: {e}")
        error_msg = ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"])
        await message.answer(error_msg)

async def send_verdict(message: Message, state: FSMContext, verdict: dict, user_id: int, language: str):
    log_verdict(user_id, verdict["pattern_label"], language)
    
    text = f"📊 **{verdict['pattern_label']}**\n\n"
    text += f"{verdict['analysis']}\n\n"
    
    if verdict.get('safety_note'):
        text += f"⚠️ **{verdict['safety_note']}**\n\n"
    
    text += f"⚡ **{verdict['immediate_technique']['label']}**: {verdict['immediate_technique']['name']}\n"
    
    for i, step in enumerate(verdict['immediate_technique']['steps'], 1):
        text += f"{i}. {step}\n"
    
    text += f"\n💡 Пример: {verdict['immediate_technique']['example']}\n\n"
    text += "📋 **Стратегия:**\n"
    
    for i, action in enumerate(verdict['strategy'], 1):
        text += f"\n{i}. {action['action']}\n"
        text += f"   Механизм: {action['mechanism']}\n"
        text += f"   Критерий: {action['criterion']}\n"
    
    await message.answer(text, parse_mode="Markdown")
    
    await storage.clear_session(user_id)
    await state.clear()
    
    end_msg = SESSION_ENDED_MESSAGES.get(language, SESSION_ENDED_MESSAGES["en"])
    await message.answer(end_msg)
