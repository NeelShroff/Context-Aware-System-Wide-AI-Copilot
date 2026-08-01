"""
Autonomous AI Chatbot & Memory Vision Processing Engine.
Handles multi-turn conversation, past work timeline recall from HistoryManager,
entity graph traversal from KnowledgeGraph, and live desktop screen vision via GDI capture.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.history_manager import HistoryManager
from src.knowledge_graph import KnowledgeGraph
from src.screen_vision import ScreenVisionEngine
from src.llm_client import LLMClient
from src.config import config

logger = logging.getLogger("AutonomousChatEngine")
logger.setLevel(logging.INFO)


class AutonomousChatEngine:
    """
    Autonomous Chatbot Engine that automatically determines required context
    (Screen Vision, Knowledge Graph Memory, History Timeline) and resolves user queries.
    """

    @staticmethod
    def detect_required_context(user_message: str, active_context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Analyzes user message to automatically detect required context layers.
        """
        msg_lower = user_message.lower()

        # Keywords triggering live screen capture vision
        screen_keywords = [
            "screen", "look at", "what am i looking at", "summarize screen",
            "this window", "this error", "stack trace", "read this", "on screen",
            "this page", "this file", "active window", "current screen"
        ]

        # Keywords triggering past work timeline / Knowledge Graph recall
        history_keywords = [
            "yesterday", "earlier", "past work", "previous session", "what did i do",
            "history", "what did we fix", "last time", "timeline", "remember",
            "what was i working on", "built", "edited", "modified", "previous code"
        ]

        need_screen = any(kw in msg_lower for kw in screen_keywords)
        need_history = any(kw in msg_lower for kw in history_keywords) or len(msg_lower) < 15

        return {
            "need_screen": need_screen,
            "need_history": need_history,
            "need_kg": True  # Always include relevant Knowledge Graph entities
        }

    @classmethod
    def process_unified_chat(cls, user_message: str, active_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes a unified chat query, automatically fetching screen vision, history, or graph memories as needed.
        """
        if active_context is None:
            active_context = {}

        process_name = str(active_context.get("process", "Desktop"))
        title = str(active_context.get("title", ""))

        # 1. Detect required context layers
        flags = cls.detect_required_context(user_message, active_context)
        
        # 2. Capture live desktop screenshot if screen context is requested
        screenshot_path = None
        if flags["need_screen"]:
            try:
                temp_ss = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "copilot_chat_ss.png")
                if ScreenVisionEngine.capture_full_screen(temp_ss):
                    screenshot_path = temp_ss
            except Exception as e:
                logger.warning(f"Screen capture exception: {e}")

        # 3. Retrieve Past History Timeline & Knowledge Graph Memories
        history_mgr = HistoryManager()
        kg_engine = KnowledgeGraph()

        recent_timeline = history_mgr.get_chronological_timeline(limit=6)
        kg_memories = kg_engine.query_context(
            process_name, title, user_message, max_items=5, screenshot_path=screenshot_path
        )

        # 4. Construct System & User Prompts
        system_prompt = (
            "You are the System-Wide AI Desktop Companion (Spider-Man Assistant), an intelligent, context-aware AI partner embedded directly into the user's OS desktop.\n\n"
            "CORE RESPONSIBILITIES & BEHAVIOR:\n"
            "- Direct, High-Impact Answers: Provide helpful, direct, and actionable solutions without unnecessary fluff or wordy meta-commentary.\n"
            "- Rich Visual & Technical Formatting: Use clean Markdown with bold key points, bullet lists, section headers, and syntax-highlighted code blocks where applicable.\n"
            "- Vision & Desktop Awareness: When analyzing an attached desktop screen capture, examine visual elements (UI status, error stack traces, open code, terminal logs) and offer precise guidance.\n"
            "- Temporal & Contextual Awareness: Leverage active window metadata, recent chronological activity, and knowledge graph memories to maintain continuity across multi-turn interactions.\n"
            "- NO RAW THINK TAGS: Do NOT output raw <think> tags or reasoning dumps."
        )

        context_blocks = []
        if active_context:
            context_blocks.append(f"<active_desktop_context process=\"{process_name}\" window_title=\"{title}\"/>")

        if recent_timeline:
            timeline_items = "\n".join([f"  <event>{t}</event>" for t in recent_timeline if isinstance(t, str)])
            if timeline_items:
                context_blocks.append(f"<recent_activity_timeline>\n{timeline_items}\n</recent_activity_timeline>")

        if kg_memories:
            kg_items = "\n".join([f"  <memory entity=\"{m.get('entity', '')}\" domain=\"{m.get('domain', '')}\"/>" for m in kg_memories if isinstance(m, dict)])
            if kg_items:
                context_blocks.append(f"<knowledge_graph_memory>\n{kg_items}\n</knowledge_graph_memory>")

        combined_context = "\n".join(context_blocks)
        full_user_prompt = f"RUNTIME CONTEXT:\n{combined_context}\n\nUSER QUESTION / COMMAND:\n{user_message}"

        # 5. Dispatch to Groq LLM API
        llm = LLMClient()
        if screenshot_path and os.path.exists(screenshot_path):
            llm_res = llm.generate_rewrite(
                system_prompt,
                f"Analyze the attached desktop screen capture and answer this request:\n{user_message}\n\nActive Application: {process_name} | Window: {title}",
                image_path=screenshot_path
            )
        else:
            llm_res = llm.generate_rewrite(system_prompt, full_user_prompt)

        if not llm_res.get("success"):
            return {
                "success": False,
                "reply": f"Unable to generate response: {llm_res.get('error')}",
                "sources": []
            }

        reply_text = llm_res.get("rewritten_text", "").strip()

        # Clean temp screenshot file
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except Exception:
                pass

        return {
            "success": True,
            "reply": reply_text,
            "context_flags": flags,
            "sources": [process_name, title] if title else [process_name]
        }
