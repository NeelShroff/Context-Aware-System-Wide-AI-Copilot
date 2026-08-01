from typing import Dict, Any
from src.context_detector import (
    SCENARIO_AI_PROMPT,
    SCENARIO_PERSONAL_CHAT,
    SCENARIO_PROFESSIONAL_CHAT,
    SCENARIO_EMAIL,
    SCENARIO_GITHUB_ISSUE,
    SCENARIO_LINKEDIN,
    SCENARIO_SOURCE_CODE,
    SCENARIO_TECH_DOCS,
    SCENARIO_GENERAL
)

SYSTEM_CORE_RULES = """
You are an intelligent, context-aware writing copilot embedded into the Windows operating system.
Your mission is to understand WHAT the user is writing, WHERE they are writing it, and WHO they are writing to, then rewrite the selected text to optimize it for that specific scenario while preserving original intent.

OUTPUT QUALITY & FORMATTING STANDARDS:
- Produce clear, concise, and beautifully structured responses.
- Use proper grammar, punctuation, and consistent Markdown formatting.
- Structure information with headings, bullet points, or numbered lists where appropriate.
- Avoid unnecessary filler words, fluff, or repetitions.
- Ensure the tone is professional, accessible, and easy to digest.

CRITICAL GUARDRAILS & RULES:
1. PRESERVE FACTUAL INTENT: Never fabricate facts, invent features, or alter names, URLs, emails, phone numbers, code snippets, commands, API endpoints, version numbers, or filenames.
2. OPTIMAL TEXT PRESERVATION: If the original text is already excellent and needs no rewrite, return it EXACTLY AS-IS without making unnecessary edits.
3. OUTPUT ONLY THE REWRITTEN MESSAGE TEXT: Do NOT include scenario titles, section headers (e.g., "### Casual Greeting" or "### Refined Text"), meta-commentary, explanations, preambles (e.g., "Here is your rewritten text:"), or surrounding quotes unless they were in the original text.
4. FORMATTING: Preserve original markdown formatting (lists, code blocks) ONLY if present in the user's original text. Do NOT add new headings or section titles.
5. KNOWLEDGE GRAPH & TEMPORAL CONTINUITY: Actively leverage the provided Knowledge Graph Memory, Application Writing History, and Chronological Activity Timeline to maintain conversational continuity, reference past context/entities/recipients, and answer with full temporal awareness whenever the user's input references past events, previous prompts, or ongoing work.
"""


from typing import Dict, Any, List, Optional

class PromptBuilder:
    """
    Constructs context-aware system and user prompts for the LLM.
    """

    @staticmethod
    def build_prompts(
        scenario: str,
        scenario_desc: str,
        context: Dict[str, Any],
        text: str,
        app_history: Optional[List[Dict[str, Any]]] = None,
        kg_memories: Optional[List[str]] = None,
        has_image: bool = False,
        chronological_timeline: Optional[List[str]] = None,
        domain_info: tuple[str, str] = ("GENERAL", "General Domain"),
        preference_rules: Optional[List[str]] = None,
        workspace_meta: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) with Time-Aware Timeline, Multi-Domain Context, Adaptive Rules, and Workspace Metadata.
        """
        title = context.get("title", "Unknown")
        process = context.get("process", "Unknown")
        domain_code, domain_desc = domain_info

        scenario_instructions = PromptBuilder._get_scenario_instructions(scenario)

        image_directive = ""
        if has_image:
            image_directive = """
MULTIMODAL IMAGE VISION DIRECTIVE:
- An image/screenshot is attached to this request.
- Carefully examine the visual contents of the image (UI status, Neo4j Desktop status, code, logs, diagrams, error messages).
- Explain what is shown in the image directly and provide actionable guidance.
- Do NOT return generic templates asking for more context; analyze and explain the image content immediately.
"""

        ws_section = ""
        if workspace_meta:
            ws_name = workspace_meta.get("name", "Default Project")
            ws_cat = workspace_meta.get("category", "General")
            ws_prio = workspace_meta.get("priority", "NORMAL")
            ws_section = f"\n- Active Workspace: {ws_name} [Category: {ws_cat} | Priority: {ws_prio}]"

        timeline_section = ""
        if chronological_timeline:
            timeline_section = "\n\nRECENT CHRONOLOGICAL ACTIVITY TIMELINE (Time & Past Interactions):\n" + "\n".join(f"• {t}" for t in chronological_timeline) + "\n* Use the chronological timeline above to understand what the user was texting or working on previously, and automatically frame your response with full temporal awareness."

        pref_section = ""
        if preference_rules:
            pref_section = "\n\nLEARNED USER BEHAVIOR & ADAPTATION RULES:\n" + "\n".join(f"• {r}" for r in preference_rules)

        memory_section = ""
        if kg_memories:
            memory_section += "\n- Relevant Knowledge Graph Memory:\n  " + "\n  ".join(f"• {m}" for m in kg_memories)
        
        if app_history:
            history_snippets = []
            for entry in app_history[-3:]:
                orig = entry.get("original_text", "")
                rew = entry.get("rewritten_text", "")
                history_snippets.append(f"  • Past Input: '{orig[:60]}...' -> Past Output: '{rew[:60]}...'")
            memory_section += "\n- Recent Application Writing History:\n" + "\n".join(history_snippets)

        system_prompt = f"{SYSTEM_CORE_RULES}\n\nCURRENT CONTEXT:\n- Active Graph Domain: {domain_code} ({domain_desc}){ws_section}\n- Detected Scenario: {scenario_desc} ({scenario})\n- Active Window Title: {title}\n- Active Process: {process}{memory_section}{timeline_section}{pref_section}{image_directive}\n\nSCENARIO SPECIFIC DIRECTIVES:\n{scenario_instructions}"

        user_prompt = f"Selected Text to Process:\n\"\"\"\n{text}\n\"\"\""

        return system_prompt, user_prompt

    @staticmethod
    def _get_scenario_instructions(scenario: str) -> str:
        if scenario == SCENARIO_AI_PROMPT:
            return """
MODE: AI PROMPT ENGINEERING MODE (Active AI Interface Detected)
The user is writing a prompt intended to be executed by an AI system (e.g. Antigravity, ChatGPT, Claude, Cursor, Copilot).
Your goal is to transform their raw input into an expert-level, highly effective AI prompt.
- Improve clarity, remove ambiguity, and structure requirements logically.
- Separate core task goals, background context, and constraints.
- Make expected outputs deterministic and precise.
- Expand vague prompts into clear, actionable instructions without inventing unauthorized features.
- Include acceptance criteria or relevant edge cases if helpful.
- Keep output concise and formatted nicely in Markdown for an LLM to execute seamlessly.
"""

        elif scenario == SCENARIO_PERSONAL_CHAT:
            return """
MODE: PERSONAL MESSAGING (WhatsApp / Telegram / Discord / Chat)
- Preserve personality, humor, and casual language.
- DO NOT make the message sound corporate, robotic, or AI-written.
- Improve clarity and correct major grammar errors while keeping it completely natural and conversational.

MULTILINGUAL & ROMANIZED INDIAN LANGUAGE SUPPORT (CRITICAL):
- The user may write in ROMANIZED INDIAN LANGUAGES — i.e., Gujarati, Hindi, Marathi, Bengali, Tamil, Telugu, etc. typed using English/Latin letters (e.g. "su kara chee tu, mana late thsa" is Romanized Gujarati meaning "what are you doing? I am going to be late").
- DO NOT confuse romanized Indian language text with gibberish, typos, or a language barrier error.
- Detect the romanized language from context and understanding of common phonetics and vocabulary.
- Refine and fix ONLY within that same romanized language — correct spelling of romanized words, fix grammar for that language, and return in the same style (romanized, not native script).
- NEVER translate romanized Indian language text into English unless the original text explicitly mixes both and would benefit from it.
- Preserve the casual, informal tone and any abbreviations/slang commonly used in that language.
"""

        elif scenario == SCENARIO_PROFESSIONAL_CHAT:
            return """
MODE: WORKPLACE CHAT (Slack / Microsoft Teams / Mattermost)
- Keep messages concise, direct, professional, yet conversational.
- Eliminate unnecessary filler words and fluff.
- Make key points easy to read at a glance.
"""

        elif scenario == SCENARIO_EMAIL:
            return """
MODE: BUSINESS EMAIL (Outlook / Gmail / Webmail)
- Produce polished, professional business writing.
- Improve structure, readability, and paragraph flow.
- Add or improve appropriate professional greetings/closings only if natural.
"""

        elif scenario == SCENARIO_GITHUB_ISSUE:
            return """
MODE: GITHUB ISSUE / BUG REPORT / PR
- Transform rough notes into a clean, structured bug report or issue description.
- Use clear Markdown sections: ### Summary, ### Expected Behavior, ### Actual Behavior, ### Steps to Reproduce (if relevant).
"""

        elif scenario == SCENARIO_LINKEDIN:
            return """
MODE: LINKEDIN / SOCIAL MEDIA
- Write in a polished, engaging, professional style.
- Ensure excellent readability and strong paragraph flow.
- Avoid generic AI buzzwords, corporate jargon overload, or cringey hype.
"""

        elif scenario == SCENARIO_SOURCE_CODE:
            return """
MODE: SOURCE CODE & DOCUMENTATION (IDE Active)
- CRITICAL: NEVER REWRITE OR ALTER THE EXECUTABLE SOURCE CODE SYNTAX!
- Only improve comments, docstrings, function headers, and inline documentation.
- Maintain exact code formatting, variable names, and language syntax.
"""

        elif scenario == SCENARIO_TECH_DOCS:
            return """
MODE: TECHNICAL DOCUMENTATION
- Improve clarity, structure, and technical readability.
- Retain exact technical terminology and code identifiers.
- Preserve all Markdown elements (headings, tables, bullet points, code blocks).
"""

        else: # SCENARIO_GENERAL
            return """
MODE: GENERAL CONTEXT-AWARE WRITING
- Intelligently refine the text for clarity, tone, and correct grammar.
- Adapt length and vocabulary dynamically to fit the context.
- Keep the writing natural and human.
"""
