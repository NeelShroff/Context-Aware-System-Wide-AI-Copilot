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
Your mission is to analyze the user's selected text along with their current application context, active window, recent activity history, and memory graph, then return an optimized, high-quality rewrite of the selected text.

CRITICAL OUTPUT CONSTRAINTS & FORMATTING RULES:
1. OUTPUT ONLY THE FINAL TEXT: Your output will directly replace the user's selected text in their active application. Do NOT include preambles (e.g. "Here is your rewritten text:"), conversational filler, postscripts, explanations, or surrounding quotation marks unless quotes were in the original text.
2. PRESERVE FACTUAL INTENT & ENTITIES: Never alter names, URLs, email addresses, phone numbers, exact numbers, API keys, passwords, filenames, or technical version identifiers.
3. OPTIMAL TEXT PRESERVATION: If the original text is already well-written and effective for the scenario, return it EXACTLY AS-IS without making unnecessary trivial edits.
4. MARKDOWN & STRUCTURE: Preserve existing markdown formatting (code blocks, bullet points) if present in the original text. Only introduce section headers if specified by the scenario directive (e.g. GitHub Issue, Bug Report, AI Prompt).
5. CONTEXT ISOLATION: Use the provided context metadata, knowledge graph memories, and activity timelines ONLY to understand background intent. NEVER output or repeat raw context fields, window titles, or memory tags in your response.
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
        workspace_meta: Optional[Dict[str, Any]] = None,
        is_voice: bool = False
    ) -> tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) using XML-tagged context structures for optimal LLM parsing.
        """
        title = context.get("title", "Unknown")
        process = context.get("process", "Unknown")
        domain_code, domain_desc = domain_info

        scenario_instructions = PromptBuilder._get_scenario_instructions(scenario)

        image_directive = ""
        if has_image:
            image_directive = """
<vision_directive>
MULTIMODAL IMAGE VISION ACTIVE:
- An image/screenshot is attached.
- Inspect the visual details (UI state, error logs, code snippet, active chat header).
- Incorporate visual findings directly into the response optimization.
</vision_directive>
"""

        voice_directive = ""
        if is_voice:
            voice_directive = f"""
<voice_command_and_vision_directive>
SPOKEN VOICE COMMAND & SCREEN VISION MODE ACTIVE:
- The user spoke a live voice instruction or query via microphone.
- The active application window metadata and desktop screen capture image are attached to provide visual context.

INTELLIGENT DUAL-MODE RESOLUTION:
1. ASSISTIVE RESPONSE / SCREEN QUERY (e.g., "What should I reply?", "How do I fix this error?", "Summarize what's on screen", "What am I looking at?"):
   - Inspect the attached screen capture (messages, email thread, code error, browser document) and active window metadata.
   - Formulate a helpful answer or draft an appropriate, high-quality response for {scenario_desc}.

2. DIRECT DICTATION / COMMAND (e.g., "Tell him I'll be late", "Reply agreeing to tomorrow at 3pm", "Add docstring for this function"):
   - Generate a polished text response suited for {scenario_desc} to be inserted directly into the user's active application text box.
   - Clean up speech stutters, false starts, filler words ("um", "uh", "like", "you know"), and unintentional repetitions.
</voice_command_and_vision_directive>
"""


        ws_meta_str = ""
        if workspace_meta:
            ws_name = workspace_meta.get("name", "Default Project")
            ws_cat = workspace_meta.get("category", "General")
            ws_prio = workspace_meta.get("priority", "NORMAL")
            ws_meta_str = f"\n  <active_workspace name=\"{ws_name}\" category=\"{ws_cat}\" priority=\"{ws_prio}\"/>"

        context_xml = f"""
<context_metadata>
  <active_window title="{title}" process="{process}"/>
  <graph_domain code="{domain_code}" description="{domain_desc}"/>
  <detected_scenario code="{scenario}" description="{scenario_desc}"/>{ws_meta_str}
</context_metadata>
"""

        memories_xml = ""
        if kg_memories or app_history:
            memories_xml = "\n<knowledge_graph_memory>\n"
            if kg_memories:
                memories_xml += "  <retrieved_entities>\n" + "\n".join(f"    <entity>{m}</entity>" for m in kg_memories[:3]) + "\n  </retrieved_entities>\n"
            if app_history:
                memories_xml += "  <recent_app_history>\n"
                for entry in app_history[-2:]:
                    orig = entry.get("original_text", "")[:50]
                    rew = entry.get("rewritten_text", "")[:50]
                    memories_xml += f"    <history_item input=\"{orig}\" output=\"{rew}\"/>\n"
                memories_xml += "  </recent_app_history>\n"
            memories_xml += "</knowledge_graph_memory>"

        timeline_xml = ""
        if chronological_timeline:
            timeline_items = "\n".join(f"  <event>{t}</event>" for t in chronological_timeline[-3:])
            timeline_xml = f"\n<chronological_activity_timeline>\n{timeline_items}\n</chronological_activity_timeline>"

        prefs_xml = ""
        if preference_rules:
            pref_items = "\n".join(f"  <rule>{r}</rule>" for r in preference_rules)
            prefs_xml = f"\n<user_preferences>\n{pref_items}\n</user_preferences>"

        system_prompt = (
            f"{SYSTEM_CORE_RULES}\n\n"
            f"RUNTIME CONTEXT METADATA:\n"
            f"{context_xml}{memories_xml}{timeline_xml}{prefs_xml}{image_directive}{voice_directive}\n\n"
            f"SCENARIO DIRECTIVES:\n{scenario_instructions}"
        )

        user_prompt = f"SELECTED TEXT TO REWRITE:\n\"\"\"\n{text}\n\"\"\"" if not is_voice else f"SPOKEN TRANSCRIPTION TO POLISH & INSERT:\n\"\"\"\n{text}\n\"\"\""

        return system_prompt, user_prompt


    @staticmethod
    def _get_scenario_instructions(scenario: str) -> str:
        if scenario == SCENARIO_AI_PROMPT:
            return """
MODE: AI PROMPT REFINEMENT MODE (Active AI / IDE Interface Detected)
The user is writing a prompt intended to be executed by an AI system (Antigravity, ChatGPT, Claude, Cursor, Copilot).
Your goal is to refine and polish their prompt so it is clear, effective, and direct while remaining compact and token-efficient.

RULES FOR PROMPT REFINEMENT:
- COMPACT & DIRECT: Keep the refined prompt concise and ready to execute. DO NOT generate bloated section templates (like [Role], [Context], [Instructions]) or wordy boilerplate that wastes input tokens.
- ENHANCE CLARITY: Remove ambiguity, fix typos/grammar, and state the objective clearly and precisely.
- PRESERVE LENGTH REASONABLY: Improve the original prompt directly without ballooning token count. Expand only if essential details were missing.
- RETURN ONLY THE REFINED PROMPT: Output ONLY the improved prompt text with zero introductory or closing commentary.
"""

        elif scenario == SCENARIO_PERSONAL_CHAT:
            return """
MODE: PERSONAL MESSAGING (WhatsApp / Telegram / Discord / Chat)
- Refine the text so it is natural, friendly, and human.
- Correct grammar and spelling errors without making the message sound robotic, stiff, or corporate.
- Maintain original emotional tone, humor, casual slang, and abbreviations.

MULTILINGUAL & ROMANIZED INDIAN LANGUAGE DIRECTIVE (CRITICAL):
- The user may type in ROMANIZED INDIAN LANGUAGES (e.g., Gujarati, Hindi, Hinglish, Marathi, Bengali, Tamil, Telugu written with Latin/English letters).
- Example: "kem cho tame, tame late thya kal" (Romanized Gujarati) or "mai kal aunga, wait karna" (Romanized Hindi).
- DO NOT treat Romanized Indian languages as typos or gibberish.
- Detect the Romanized language and refine spelling, phonetics, and grammar strictly WITHIN that same Romanized language.
- DO NOT translate Romanized text into English unless the user explicitly requested translation.
- Preserve casual phonetic spellings and colloquial phrasing.
"""

        elif scenario == SCENARIO_PROFESSIONAL_CHAT:
            return """
MODE: WORKPLACE CHAT (Slack / Microsoft Teams / Mattermost)
- Produce concise, clear, and professional workplace communication.
- Remove filler words and wordy preambles.
- Make key action items or updates easy to scan at a glance.
- Keep the tone polite, professional, and efficient.
"""

        elif scenario == SCENARIO_EMAIL:
            return """
MODE: BUSINESS EMAIL (Outlook / Gmail / Webmail)
- Produce polished, professional business email text with smooth paragraph transitions.
- Ensure appropriate greetings and sign-offs if the text represents a complete email draft.
- Enhance clarity, tone, and professional courtesy while preserving core decisions and call-to-actions.
"""

        elif scenario == SCENARIO_GITHUB_ISSUE:
            return """
MODE: GITHUB ISSUE / BUG REPORT / PR DESCRIPTION
- Format rough notes into a clean, structured GitHub Issue or PR description using Markdown.
- Organize logically into standard headers:
  ### Summary
  ### Expected Behavior
  ### Actual Behavior
  ### Steps to Reproduce (or Implementation Details)
- Keep descriptions precise, technical, and actionable for developers.
"""

        elif scenario == SCENARIO_LINKEDIN:
            return """
MODE: LINKEDIN / SOCIAL MEDIA
- Craft an engaging, professional social media post with strong paragraph readability.
- Maintain an authoritative yet authentic voice. Avoid cringey hype, excessive emojis, or generic AI buzzwords.
- Use clean line breaks for comfortable mobile scanning.
"""

        elif scenario == SCENARIO_SOURCE_CODE:
            return """
MODE: SOURCE CODE & DOCUMENTATION (IDE Active)
- If the user selected code comments or docstrings, refine them for clarity, accuracy, and proper formatting.
- If the user selected executable source code, improve code quality, fix bugs, or format code syntax cleanly while preserving existing variable names, functional logic, and language conventions.
- Return valid code/documentation without surrounding explanations.
"""

        elif scenario == SCENARIO_TECH_DOCS:
            return """
MODE: TECHNICAL DOCUMENTATION
- Enhance technical clarity, precision, and structural flow.
- Maintain accurate terminology, code blocks, parameter names, and API specifications.
- Use clear bullet points and bold highlights for readability.
"""

        else: # SCENARIO_GENERAL
            return """
MODE: GENERAL CONTEXT-AWARE WRITING
- Refine text for clarity, conciseness, proper grammar, and natural flow.
- Adapt tone and vocabulary dynamically based on the context.
- Keep the output natural, direct, and human.
"""

