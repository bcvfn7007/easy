import openai
from typing import List, Dict
from app.config.settings import config
from app.utils.logger import setup_logger

logger = setup_logger("ai_provider")

# OpenRouter is OpenAI compatible.
# meta-llama/llama-3-8b-instruct is an excellent, free open-source model available on OpenRouter.
# Auto-detect Groq API vs OpenRouter based on key prefix
# Groq keys start with 'gsk_' and offer blazing fast FREE Llama 3 models.
if config.OPENROUTER_API_KEY and config.OPENROUTER_API_KEY.startswith("gsk_"):
    _BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.1-8b-instant"
else:
    _BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "google/gemma-2-9b-it:free"

CLIENT = openai.AsyncOpenAI(
    base_url=_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """
You are 'Easy English', a highly perceptive and friendly English language tutor AI.
Your goals:
1. Converse naturally with the user to help them practice English.
2. If the user makes grammatical, spelling, or unnatural phrasing errors, GENTLY correct them before continuing the conversation.
3. Explain the correction in simple terms.
4. CRITICAL: Your explanation language MUST match the user's native language. If the user speaks Russian, explain the English rules in Russian. If they speak Spanish, explain in Spanish.
5. Keep your responses relatively short, suitable for a Telegram message.
"""

async def generate_response(user_id: int, history: List[Dict[str, str]], new_message: str) -> str:
    """
    Generate an AI response based on conversation history and the new message.
    """
    if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY.startswith("your_"):
         logger.warning("OpenRouter API key is not configured!")
         return "It looks like my AI core is currently sleeping. Please tell the admin to configure the API key."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Append history (limited usually to last N messages which is handled by the model layer limit)
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": new_message})
    
    try:
        response = await CLIENT.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            # Adjust max tokens to keep replies concise for Telegram/Voice
            max_tokens=250,
            temperature=0.7
        )
        reply = response.choices[0].message.content
        return reply.strip()
    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return f"I'm having a little trouble thinking of what to say right now.\n\n(Debug Error: {str(e)})"
