import openai
from typing import List, Dict
from app.config.settings import config
from app.utils.logger import setup_logger
from app.services.base import BaseAIProvider

logger = setup_logger("ai_provider")

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

SYSTEM_PROMPT_TEMPLATE = """
You are 'Easy English', a highly perceptive, incredibly supportive, and charismatic English language coach.
The user playing with you currently has an English Grammar Level of: {grammar_level}.

Your goals:
1. Converse naturally and engagingly with the user to help them practice English. Always ask a compelling follow-up question to keep the conversation flowing.
2. If the user makes grammatical, spelling, or unnatural phrasing errors, GENTLY correct them before continuing the conversation. Tailor your corrections and response complexity to their grammar level ({grammar_level}).
3. CRITICAL REQUIREMENT: Your corrections MUST be formatted specifically like this on individual lines (use these exact emojis):
❌ Error: [the exact phrase they got wrong]
✅ Correction: [the correct phrase]
💡 Rule: [very brief, encouraging explanation of why, in the user's native language]

4. Your rule explanation MUST match the user's native language. If the user speaks Russian, explain the English rules in Russian.
5. After the correction block, continue the conversation naturally in English. Be witty, interesting, and act like a real language partner!
"""

class OpenRouterAI(BaseAIProvider):
    """OpenRouter API implementation for AI chat."""
    
    async def generate_response(self, user_id: int, history: List[Dict[str, str]], new_message: str, grammar_level: str = "Intermediate") -> str:
        """Generate an AI response based on history and new message."""
        if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY.startswith("your_"):
             logger.warning("OpenRouter API key is not configured!")
             return "It looks like my AI core is currently sleeping. Please tell the admin to configure the API key."

        prompt = SYSTEM_PROMPT_TEMPLATE.format(grammar_level=grammar_level)
        messages = [{"role": "system", "content": prompt}]
        
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": new_message})
        
        try:
            response = await CLIENT.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=250,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            return reply.strip()
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return f"I'm having a little trouble thinking of what to say right now.\n\n(Debug Error: {str(e)})"
