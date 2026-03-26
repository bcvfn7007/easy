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

BASE_PROMPT = """
You are an advanced English language coach. The user playing with you has an English Grammar Level of: {grammar_level}.

CRITICAL REQUIREMENT: Your corrections MUST be formatted specifically like this on individual lines (use these exact emojis):
❌ Error: [the exact phrase they got wrong]
✅ Correction: [the correct phrase]
💡 Rule: [very brief, encouraging explanation of why, in the user's native language]

Your rule explanation MUST match the user's native language. If the user speaks Russian, explain the English rules in Russian.
After the correction block, continue the conversation based on your CURRENT ROLE.
"""

ROLE_PROMPTS = {
    "Casual": "CURRENT ROLE: A charismatic and witty language partner. Converse naturally and engagingly. Always ask a compelling follow-up question to keep the conversation flowing.",
    "IELTS": "CURRENT ROLE: A strict but fair IELTS Speaking Examiner. Start by welcoming the candidate and asking Part 1 questions. Then move to a Part 2 cue card, and finally Part 3 abstract questions. Keep it highly realistic to the IELTS exam format. Occasionally give them a quick estimated Band Score on their answer.",
    "Interview": "CURRENT ROLE: A Professional Hiring Manager at a Tech Company. Ask realistic HR and technical behavioral questions (e.g. 'Tell me about a time you resolved a conflict'). Act exactly like an interviewer.",
    "Travel": "CURRENT ROLE: Various people the user meets while traveling (e.g., a Customs Officer, a Hotel Receptionist, a Waiter). Play the scenario realistically so the user can practice survival English."
}

class OpenRouterAI(BaseAIProvider):
    """OpenRouter API implementation for AI chat."""
    
    async def generate_response(self, user_id: int, history: List[Dict[str, str]], new_message: str, grammar_level: str = "Intermediate", bot_mode: str = "Casual") -> str:
        """Generate an AI response based on history and new message."""
        if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY.startswith("your_"):
             logger.warning("OpenRouter API key is not configured!")
             return "It looks like my AI core is currently sleeping. Please tell the admin to configure the API key."

        prompt = BASE_PROMPT.format(grammar_level=grammar_level)
        role_prompt = ROLE_PROMPTS.get(bot_mode, ROLE_PROMPTS["Casual"])
        full_system_prompt = prompt + "\n\n" + role_prompt
        
        messages = [{"role": "system", "content": full_system_prompt}]
        
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
