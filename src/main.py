import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.context_detector import ContextDetector
from src.prompt_builder import PromptBuilder
from src.llm_client import LLMClient


def process_request(input_data: Dict[str, Any]) -> Dict[str, Any]:
    text = input_data.get("text", "")
    context = input_data.get("context", {})

    if not text or len(text.strip()) == 0:
        return {
            "success": False,
            "scenario": "UNKNOWN",
            "scenario_description": "No Text Provided",
            "original_text": "",
            "rewritten_text": "",
            "changed": False,
            "error": "No text was selected."
        }

    # 1. Detect Scenario
    scenario, scenario_desc = ContextDetector.detect_scenario(context, text)

    # 2. Build Adaptive Prompts
    system_prompt, user_prompt = PromptBuilder.build_prompts(scenario, scenario_desc, context, text)

    # 3. Call LLM
    llm = LLMClient()
    llm_result = llm.generate_rewrite(system_prompt, user_prompt)

    if not llm_result["success"]:
        return {
            "success": False,
            "scenario": scenario,
            "scenario_description": scenario_desc,
            "original_text": text,
            "rewritten_text": text,
            "changed": False,
            "error": llm_result["error"]
        }

    rewritten_text = llm_result["rewritten_text"]
    changed = (rewritten_text != text)

    return {
        "success": True,
        "scenario": scenario,
        "scenario_description": scenario_desc,
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
    parser.add_argument("--stdin", action="store_true", help="Read input JSON from standard input")

    args = parser.parse_args()

    input_data = {}
    if args.stdin:
        raw_in = sys.stdin.read()
        if raw_in.strip():
            input_data = json.loads(raw_in)
    elif args.input_file and os.path.exists(args.input_file):
        with open(args.input_file, "r", encoding="utf-8-sig") as f:
            input_data = json.load(f)
    else:
        # Fallback if invoked without arguments
        sys.stderr.write("Usage: python main.py <input_file.json> OR python main.py --stdin\n")
        sys.exit(1)

    result = process_request(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
