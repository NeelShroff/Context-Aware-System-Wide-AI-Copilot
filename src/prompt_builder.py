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

CRITICAL GUARDRAILS & RULES:
1. PRESERVE FACTUAL INTENT: Never fabricate facts, invent features, or alter names, URLs, emails, phone numbers, code snippets, commands, API endpoints, version numbers, or filenames.
2. OPTIMAL TEXT PRESERVATION: If the original text is already excellent and needs no rewrite, return it EXACTLY AS-IS without making unnecessary edits.
3. OUTPUT ONLY THE REWRITTEN TEXT: Do not include meta-commentary, explanations, preambles (e.g., "Here is your rewritten text:"), or surrounding quotes unless they were in the original.
4. FORMATTING: Preserve Markdown formatting, headings, code blocks, lists, and indentation where applicable.
"""


class PromptBuilder:
    """
    Constructs context-aware system and user prompts for the LLM.
    """

    @staticmethod
    def build_prompts(scenario: str, scenario_desc: str, context: Dict[str, Any], text: str) -> tuple[str, str]:
        """
        Returns (system_prompt, user_prompt)
        """
        title = context.get("title", "Unknown")
        process = context.get("process", "Unknown")

        scenario_instructions = PromptBuilder._get_scenario_instructions(scenario)

        system_prompt = f"{SYSTEM_CORE_RULES}\n\nCURRENT CONTEXT:\n- Detected Scenario: {scenario_desc} ({scenario})\n- Active Window Title: {title}\n- Active Process: {process}\n\nSCENARIO SPECIFIC DIRECTIVES:\n{scenario_instructions}"

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
