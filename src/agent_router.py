"""
Agent Intent Router — LLM Autonomous Tool Calling.
Uses LLM Function/Tool Declarations to autonomously determine user intent:
- Music Playback / Control (play_music, pause_music, resume_music, stop_music)
- Timed Reminders (set_reminder)
- Long-Term Memory (save_user_fact)
- Real-Time Web Search (search_web)
- Text Dictation / Screen Assist (dictate_or_rewrite_text)
"""
import os
import sys
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AgentIntentRouter")
logger.setLevel(logging.INFO)

# Tool Schemas for LLM Router
AGENT_TOOLS = [
    {
        "name": "play_music",
        "description": "Play a song, artist, album, genre, or lo-fi music track on YouTube Music.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The song name, artist, or music genre to search and play"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "control_music",
        "description": "Pause, resume, unpause, or stop active background music playback.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["pause", "resume", "stop"], "description": "Playback control command"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "set_reminder",
        "description": "Set a timed reminder or countdown alarm to notify the user later.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to remind the user about"},
                "delay_seconds": {"type": "number", "description": "Delay in seconds until the reminder fires (e.g. 300 for 5 minutes)"}
            },
            "required": ["task", "delay_seconds"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Save a long-term preference or fact memory about the user or contact.",
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "The fact or preference memory to store"}
            },
            "required": ["fact"]
        }
    },
    {
        "name": "search_web",
        "description": "Search DuckDuckGo / Web for live weather, news, documentation, or real-time information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The web search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "dictate_or_rewrite_text",
        "description": "Draft, polish, or dictate text to write/paste into the active window input field, or answer a question on screen.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {"type": "string", "description": "The original or cleaned user request"}
            },
            "required": ["user_prompt"]
        }
    }
]


class AgentIntentRouter:
    """Autonomous LLM Agent Tool Calling Router."""

    @staticmethod
    def classify_and_route(text: str, context: Dict[str, Any], is_voice: bool = False) -> Optional[Dict[str, Any]]:
        """
        Uses LLM tool calling to classify user intent and execute the appropriate action tool.
        Returns a result dict if an action tool (music, reminder, memory, web search) was executed,
        or None if text dictation / screen vision prompt rewriting should handle it.
        """
        text_clean = text.strip()
        if not text_clean:
            return None

        # 1. Quick regex fast-pass for high-frequency direct commands
        text_lower = text_clean.lower()
        if "pause music" in text_lower or "pause song" in text_lower:
            from src.music_engine import MusicEngine
            res = MusicEngine.get_instance().pause()
            return {"success": True, "scenario": "MUSIC_CONTROL", "scenario_description": "Music Paused", "bubble_message": res["message"], "original_text": text, "rewritten_text": res["message"], "changed": False}

        if "stop music" in text_lower or "stop song" in text_lower:
            from src.music_engine import MusicEngine
            res = MusicEngine.get_instance().stop()
            return {"success": True, "scenario": "MUSIC_CONTROL", "scenario_description": "Music Stopped", "bubble_message": res["message"], "original_text": text, "rewritten_text": res["message"], "changed": False}

        # 2. Call Fast LLM to determine tool call choice
        from src.llm_client import LLMClient
        llm = LLMClient()

        system_prompt = (
            "You are an autonomous Voice AI Agent Intent Router.\n"
            "Analyze the user's input text and choose the single best tool to execute.\n"
            "Output JSON with fields: {\"tool\": \"tool_name\", \"args\": {...}}\n\n"
            "Tool Options:\n"
            "1. play_music: if user asks to play a song, artist, music, track, or lo-fi (e.g. 'alex warren', 'play song', 'lo-fi'). args: {\"query\": \"artist or song\"}\n"
            "2. control_music: if user asks to pause, resume, or stop music. args: {\"action\": \"pause\"|\"resume\"|\"stop\"}\n"
            "3. set_reminder: if user asks to set a reminder or alarm (e.g. 'remind me in 5 minutes'). args: {\"task\": \"task\", \"delay_seconds\": 300}\n"
            "4. save_user_fact: if user asks to remember a fact/preference (e.g. 'remember that Alex likes formal emails'). args: {\"fact\": \"fact\"}\n"
            "5. search_web: if user asks for web search, weather, news. args: {\"query\": \"search text\"}\n"
            "6. dictate_or_rewrite_text: if user is dictating text to write into active document/chat or asking a general desktop question. args: {\"user_prompt\": \"text\"}\n\n"
            "Respond ONLY with valid JSON."
        )

        user_prompt = f"User Input: '{text_clean}'\nActive App: {context.get('process', 'unknown')}\nWindow Title: {context.get('title', '')}"

        try:
            res = llm.generate_rewrite(system_prompt, user_prompt)
            if res.get("success") and res.get("rewritten_text"):
                llm_out = res["rewritten_text"].strip()
                # Clean markdown json code blocks if present
                if llm_out.startswith("```json"):
                    llm_out = llm_out[7:]
                if llm_out.startswith("```"):
                    llm_out = llm_out[3:]
                if llm_out.endswith("```"):
                    llm_out = llm_out[:-3]
                
                decision = json.loads(llm_out.strip())
                tool_name = decision.get("tool")
                args = decision.get("args", {})

                logger.info(f"Agent Router Decision: {tool_name} with args {args}")

                # Execute Selected Agent Tool
                if tool_name == "play_music":
                    from src.music_engine import MusicEngine
                    query = args.get("query") or text_clean
                    res_m = MusicEngine.get_instance().play(query)
                    return {
                        "success": True,
                        "scenario": "MUSIC_CONTROL",
                        "scenario_description": "Music Playback",
                        "bubble_message": res_m.get("message", ""),
                        "original_text": text,
                        "rewritten_text": res_m.get("message", ""),
                        "changed": False
                    }

                elif tool_name == "control_music":
                    from src.music_engine import MusicEngine
                    action = args.get("action", "stop")
                    if action == "pause":
                        res_m = MusicEngine.get_instance().pause()
                    elif action == "resume":
                        res_m = MusicEngine.get_instance().resume()
                    else:
                        res_m = MusicEngine.get_instance().stop()
                    return {
                        "success": True,
                        "scenario": "MUSIC_CONTROL",
                        "scenario_description": f"Music {action.capitalize()}",
                        "bubble_message": res_m.get("message", ""),
                        "original_text": text,
                        "rewritten_text": res_m.get("message", ""),
                        "changed": False
                    }

                elif tool_name == "set_reminder":
                    from src.reminders_manager import RemindersManager
                    rem_mgr = RemindersManager()
                    task = args.get("task", text_clean)
                    delay = float(args.get("delay_seconds", 300.0))
                    res_r = rem_mgr.add_reminder(task, delay)
                    return {
                        "success": True,
                        "scenario": "REMINDER_SET",
                        "scenario_description": "Reminder Scheduled",
                        "bubble_message": res_r.get("message", ""),
                        "original_text": text,
                        "rewritten_text": res_r.get("message", ""),
                        "changed": False
                    }

                elif tool_name == "save_user_fact":
                    from src.knowledge_graph import KnowledgeGraph
                    kg = KnowledgeGraph()
                    fact = args.get("fact", text_clean)
                    res_f = kg.save_user_fact(fact)
                    return {
                        "success": True,
                        "scenario": "MEMORY_FACT_SAVED",
                        "scenario_description": "User Fact Saved",
                        "bubble_message": res_f.get("message", ""),
                        "original_text": text,
                        "rewritten_text": res_f.get("message", ""),
                        "changed": False
                    }

        except Exception as e:
            logger.warning(f"Agent Intent Router fallback notice: {e}")

        return None
