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

CRITICAL REQUIREMENT: You MUST respond ONLY with a valid JSON object. Do not wrap the JSON in markdown blocks.
The JSON must have EXACTLY these three keys:
{{
    "correction_short": "💡 Mistake -> Correction (e.g. Can I can -> Can I use)",
    "explanation": "Brief explanation of the grammar rule in the user's native language (e.g. Russian).",
    "english_reply": "Your engaging, conversational reply in English based on your CURRENT ROLE."
}}

If the user made no grammar mistakes, set "correction_short" and "explanation" to empty strings "".
Your "english_reply" MUST NEVER contain grammar explanations. It should strictly be your conversational response.
"""

ROLE_PROMPTS = {
    "Casual": "CURRENT ROLE: A charismatic and witty language partner. Converse naturally and engagingly. Always ask a compelling follow-up question to keep the conversation flowing.",
    "IELTS": "CURRENT ROLE: A strict but fair IELTS Speaking Examiner. Start by welcoming the candidate and asking Part 1 questions. Then move to a Part 2 cue card, and finally Part 3 abstract questions. Keep it highly realistic to the IELTS exam format. Occasionally give them a quick estimated Band Score on their answer.",
    "Interview": "CURRENT ROLE: A Professional Hiring Manager at a Tech Company. Ask realistic HR and technical behavioral questions (e.g. 'Tell me about a time you resolved a conflict'). Act exactly like an interviewer.",
    "Travel": "CURRENT ROLE: Various people the user meets while traveling (e.g., a Customs Officer, a Hotel Receptionist, a Waiter). Play the scenario realistically so the user can practice survival English."
}

class OpenRouterAI(BaseAIProvider):
    """OpenRouter API implementation for AI chat."""
    
    async def generate_response(self, user_id: int, history: List[Dict[str, str]], new_message: str, grammar_level: str = "Intermediate", bot_mode: str = "Casual") -> Dict[str, str]:
        """Generate an AI response based on history and new message. Returns structured JSON dict."""
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
                max_tokens=300,
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            
            import json
            import re
            
            # If AI forgot the brackets, wrap it
            if not reply.startswith("{") and '"english_reply"' in reply:
                reply = "{" + reply + "}"
            
            # Find JSON boundaries
            match = re.search(r'\{.*\}', reply, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    return {
                        "correction_short": data.get("correction_short", ""),
                        "explanation": data.get("explanation", ""),
                        "english_reply": data.get("english_reply", reply)
                    }
                except json.JSONDecodeError:
                    pass
                    
            # Fallback string manipulation if JSON is fundamentally broken
            if '"english_reply"' in reply:
                fallback = reply.split('"english_reply"')[-1]
                fallback = fallback.replace(':', '', 1).strip().strip('"').strip('}').strip()
                return {
                    "correction_short": "",
                    "explanation": "JSON Parse Error",
                    "english_reply": fallback
                }
                
            return {
                "correction_short": "",
                "explanation": "",
                "english_reply": reply
            }
                
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return {
                "correction_short": "",
                "explanation": "",
                "english_reply": f"I'm having a little trouble thinking of what to say right now.\n\n(Debug Error: {str(e)})"
            }
