import sys
import os

# Handle windowless pythonw.exe execution where stdout/stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.context_detector import ContextDetector
from src.prompt_builder import PromptBuilder
from src.llm_client import LLMClient
from src.history_manager import HistoryManager
from src.knowledge_graph import KnowledgeGraph


from src.graph_switcher import GraphSwitcher
from src.context_manager import ContextManager
from src.adaptive_engine import AdaptiveEngine


def process_request(input_data: Dict[str, Any]) -> Dict[str, Any]:
    is_voice = bool(input_data.get("is_voice", False))
    text = input_data.get("text", "")
    context = input_data.get("context", {})
    user_domain_override = input_data.get("domain_override")

    if is_voice:
        try:
            import urllib.request
            speech_payload = json.dumps({
                "text": "🎙️ Listening... (Speak into mic)",
                "duration": 5.0,
                "mode": "THINKING"
            }).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:8799/api/speech", data=speech_payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            pass

        from src.voice_capture import dictate_to_text
        max_sec = float(input_data.get("max_seconds", 12.0))
        voice_res = dictate_to_text(max_seconds=max_sec)

        if not voice_res.get("success"):
            return {
                "success": False,
                "scenario": "VOICE_DICTATION",
                "scenario_description": "Voice Dictation Failed",
                "original_text": "",
                "rewritten_text": "",
                "changed": False,
                "error": voice_res.get("error", "No speech detected.")
            }

        text = voice_res.get("text", "").strip()
        if not text:
            return {
                "success": False,
                "scenario": "VOICE_DICTATION",
                "scenario_description": "Empty Transcription",
                "original_text": "",
                "rewritten_text": "",
                "changed": False,
                "error": "No clear speech recognized."
            }

    elif not text or len(text.strip()) == 0:
        return {
            "success": False,
            "scenario": "UNKNOWN",
            "scenario_description": "No Text Provided",
            "original_text": "",
            "rewritten_text": "",
            "changed": False,
            "error": "No text was selected."
        }

    process_name = str(context.get("process", "unknown.exe"))
    title = str(context.get("title", ""))
    text_lower = text.lower().strip()

    # --- Autonomous LLM Agent Intent Tool Router ---
    from src.agent_router import AgentIntentRouter
    agent_action_result = AgentIntentRouter.classify_and_route(text, context, is_voice=is_voice)
    if agent_action_result is not None:
        return agent_action_result


    # 1. Resolve Active Graph Domain, Scenario & Context Workspace Metadata
    domain_info = GraphSwitcher.resolve_domain(context, user_override=user_domain_override)
    domain_code, domain_desc = domain_info
    scenario, scenario_desc = ContextDetector.detect_scenario(context, text)

    project_name = input_data.get("project_name", "System-Wide AI Copilot")
    ctx_mgr = ContextManager()
    ws_info = ctx_mgr.get_workspace_metadata(project_name)
    workspace_meta = {"name": project_name, **ws_info}

    # 2. Query History, Chronological Timeline & Knowledge Graph Memory
    history_mgr = HistoryManager()
    kg_engine = KnowledgeGraph()

    screenshot_path = input_data.get("screenshot_path")
    has_screenshot = bool(screenshot_path and os.path.exists(screenshot_path))

    # Apply Spatial Grid Overlay if requested for spatial vision
    if has_screenshot and ("grid" in text_lower or "spatial" in text_lower or "region" in text_lower or "where" in text_lower):
        from src.screen_vision import ScreenVisionEngine
        ScreenVisionEngine.add_spatial_grid_overlay(screenshot_path)

    # Skip synchronous recipient extraction to avoid double LLM API calls on fast Groq path
    kg_engine._cached_recipient = None

    app_history = history_mgr.get_app_history(process_name, limit=3)
    chronological_timeline = history_mgr.get_chronological_timeline(limit=5)
    kg_memories = kg_engine.query_context(process_name, title, text, domain=domain_code, max_items=5, screenshot_path=screenshot_path)

    # Resolve ambiguous input using recent activity timeline
    recent_summary, resolved_text = AdaptiveEngine.resolve_ambiguity(text, chronological_timeline, context)

    image_path = input_data.get("image_path")
    if not image_path and has_screenshot:
        image_path = screenshot_path
    has_image = bool(image_path and os.path.exists(image_path))

    # Extract active preference rules for style adaptation
    pref_data = AdaptiveEngine.analyze_interaction(text, text, context)
    preference_rules = pref_data.get("preference_rules", [])

    # 3. Build Adaptive Prompts with Time-Aware Timeline, Multi-Domain Context, Preference Rules & Workspace Metadata
    system_prompt, user_prompt = PromptBuilder.build_prompts(
        scenario, scenario_desc, context, resolved_text,
        app_history=app_history,
        kg_memories=kg_memories,
        has_image=has_image,
        chronological_timeline=chronological_timeline,
        domain_info=domain_info,
        preference_rules=preference_rules,
        workspace_meta=workspace_meta,
        is_voice=is_voice
    )

    # --- INTENT ROUTER 4: Web Search Context Injection ---
    if "search the web" in text_lower or "search for" in text_lower or "look up" in text_lower or "weather" in text_lower:
        from src.web_search_engine import WebSearchEngine
        web_context = WebSearchEngine.format_search_context(text)
        if web_context:
            system_prompt += f"\n\n{web_context}"



    # 4. Call LLM (with Multimodal Image Support)
    llm = LLMClient()
    llm_result = llm.generate_rewrite(system_prompt, user_prompt, image_path=image_path)

    if not llm_result["success"]:
        return {
            "success": False,
            "scenario": scenario,
            "scenario_description": f"{scenario_desc} [{domain_code}]",
            "original_text": text,
            "rewritten_text": text,
            "changed": False,
            "error": llm_result["error"]
        }

    rewritten_text = llm_result["rewritten_text"]
    changed = (rewritten_text != text)

    # Classify intent & generate concise speech bubble message (NEVER post raw rewritten_text to 3D bubble)
    intent_type, bubble_message = ContextDetector.classify_response_intent(
        scenario, changed, text=text, rewritten_text=rewritten_text
    )

    # Post concise status one-liner to 3D VRM Desktop Pet server if active
    try:
        import urllib.request
        speech_payload = json.dumps({
            "text": bubble_message,
            "duration": 4.0,
            "mode": "TALKING"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8799/api/speech",
            data=speech_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass

    # 5. Analyze User Behavior Preferences & Persist Graph Updates
    pref_analysis = AdaptiveEngine.analyze_interaction(text, rewritten_text, context)
    extracted_entities = kg_engine.extract_entities(rewritten_text, context)
    
    history_mgr.record_entry(
        process_name=process_name,
        title=title,
        scenario=scenario,
        original_text=text,
        rewritten_text=rewritten_text,
        entities=extracted_entities
    )
    kg_engine.update_graph(
        extracted_entities,
        process_name,
        title,
        domain=domain_code,
        preferences=pref_analysis,
        original_text=text,
        rewritten_text=rewritten_text,
        project_name=project_name,
        workspace_meta=workspace_meta,
        screenshot_path=screenshot_path
    )

    return {
        "success": True,
        "scenario": scenario,
        "scenario_description": scenario_desc,
        "bubble_message": bubble_message,
        "intent_type": intent_type,
        "original_text": text,
        "rewritten_text": rewritten_text,
        "changed": changed,
        "error": None
    }


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="Context-Aware System-Wide AI Writing Copilot Backend")
    parser.add_argument("input_file", nargs="?", help="Path to input JSON file from AutoHotkey")
    parser.add_argument("output_file", nargs="?", help="Path to output JSON file to write results")
    parser.add_argument("--stdin", action="store_true", help="Read input JSON from standard input")
    parser.add_argument("--voice", action="store_true", help="Trigger voice dictation mode directly")

    args = parser.parse_args()

    input_data = {}
    if args.voice:
        input_data["is_voice"] = True
    elif args.stdin:
        raw_in = sys.stdin.read()
        if raw_in.strip():
            input_data = json.loads(raw_in)
    elif args.input_file and os.path.exists(args.input_file):
        with open(args.input_file, "r", encoding="utf-8-sig") as f:
            input_data = json.load(f)
    else:
        # Fallback if invoked without arguments
        sys.stderr.write("Usage: python main.py <input_file.json> [output_file.json] OR python main.py --stdin OR python main.py --voice\n")
        sys.exit(1)


    result = process_request(input_data)
    json_out = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(json_out)
    else:
        print(json_out)


if __name__ == "__main__":
    main()
