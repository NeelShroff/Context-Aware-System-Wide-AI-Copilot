import re
from typing import Dict, Any, Tuple

# Scenario Constants
SCENARIO_AI_PROMPT = "AI_PROMPT_ENGINEERING"
SCENARIO_PERSONAL_CHAT = "PERSONAL_CHAT"
SCENARIO_PROFESSIONAL_CHAT = "PROFESSIONAL_CHAT"
SCENARIO_EMAIL = "BUSINESS_EMAIL"
SCENARIO_GITHUB_ISSUE = "GITHUB_ISSUE_BUG_REPORT"
SCENARIO_LINKEDIN = "LINKEDIN_SOCIAL"
SCENARIO_SOURCE_CODE = "SOURCE_CODE_DOCS"
SCENARIO_TECH_DOCS = "TECHNICAL_DOCUMENTATION"
SCENARIO_GENERAL = "GENERAL_WRITING"


class ContextDetector:
    """
    Analyzes window title, process name, process path, window class,
    and text content to detect the exact user scenario.
    """

    @staticmethod
    def detect_scenario(context: Dict[str, Any], text: str = "") -> Tuple[str, str]:
        """
        Returns (scenario_code, scenario_description).
        """
        title = str(context.get("title", "")).lower()
        process = str(context.get("process", "")).lower()
        win_class = str(context.get("class", "")).lower()
        url = str(context.get("url", "")).lower()
        
        combined_meta = f"{title} {process} {win_class} {url}"

        # 1. Check AI Interfaces (Highest Priority for Prompt Engineering Mode)
        ai_keywords = [
            "antigravity", "chatgpt", "claude", "cursor", "windsurf",
            "copilot", "openwebui", "lm studio", "lm-studio", "ollama",
            "poe.com", "perplexity", "gemini.google", "v0.dev", "bolt.new",
            "deepseek", "groq", "openai", "huggingface"
        ]
        ai_processes = [
            "antigravity.exe", "cursor.exe", "windsurf.exe",
            "lm-studio.exe", "ollama.exe", "chatgpt.exe"
        ]
        
        if any(p in process for p in ai_processes):
            return (SCENARIO_AI_PROMPT, "AI Application / Prompt Interface")
            
        if any(kw in combined_meta for kw in ai_keywords):
            return (SCENARIO_AI_PROMPT, "AI Chat / Prompt Engineering Interface")

        # 2. Check Personal Chat
        personal_chat_procs = ["whatsapp.exe", "telegram.exe", "signal.exe", "discord.exe"]
        personal_chat_kw = ["web.whatsapp.com", "t.me", "telegram", "discord.com", "web.signal.org"]
        if any(p in process for p in personal_chat_procs) or any(kw in combined_meta for kw in personal_chat_kw):
            return (SCENARIO_PERSONAL_CHAT, "Personal Messaging (WhatsApp / Telegram / Discord)")

        # 3. Check Professional Chat
        prof_chat_procs = ["slack.exe", "teams.exe", "ms-teams.exe", "mattermost.exe"]
        prof_chat_kw = ["app.slack.com", "teams.microsoft.com", "mattermost"]
        if any(p in process for p in prof_chat_procs) or any(kw in combined_meta for kw in prof_chat_kw):
            return (SCENARIO_PROFESSIONAL_CHAT, "Professional Workplace Chat (Slack / Teams)")

        # 4. Check Business Email
        email_procs = ["outlook.exe", "thunderbird.exe"]
        email_kw = ["mail.google.com", "gmail", "outlook.office.com", "mail.live.com", "fastmail", "proton.me/mail"]
        if any(p in process for p in email_procs) or any(kw in combined_meta for kw in email_kw):
            return (SCENARIO_EMAIL, "Business / Professional Email")

        # 5. Check GitHub / Issue Tracker / Bug Reports
        github_kw = ["github.com", "github", "gitlab.com", "gitlab", "jira", "linear.app", "bug report", "issue #", "issues"]
        if any(kw in combined_meta for kw in github_kw):
            return (SCENARIO_GITHUB_ISSUE, "GitHub / Issue Tracker / Bug Report")

        # 6. Check LinkedIn & Social Media
        linkedin_kw = ["linkedin.com", "x.com", "twitter.com", "reddit.com"]
        if any(kw in combined_meta for kw in linkedin_kw):
            return (SCENARIO_LINKEDIN, "LinkedIn / Social Media")

        # 7. Check Source Code / IDEs
        ide_procs = [
            "code.exe", "pycharm64.exe", "devenv.exe", "sublime_text.exe",
            "idea64.exe", "rider64.exe", "webstorm64.exe", "clion64.exe", "npp.exe"
        ]
        if any(p in process for p in ide_procs):
            # Check if selection is predominantly code
            if ContextDetector._looks_like_code(text):
                return (SCENARIO_SOURCE_CODE, "Source Code (Comments / Documentation)")
            else:
                return (SCENARIO_TECH_DOCS, "IDE Technical Writing")

        # 8. Check Documentation Tools
        doc_procs = ["obsidian.exe", "notion.exe", "winword.exe", "typora.exe"]
        doc_kw = ["notion.so", "confluence", "docs.google.com", "readme.md"]
        if any(p in process for p in doc_procs) or any(kw in combined_meta for kw in doc_kw):
            return (SCENARIO_TECH_DOCS, "Technical Documentation")

        # Default fallback
        return (SCENARIO_GENERAL, "General Context-Aware Writing")

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        """Determines if the text selection is primarily code."""
        if not text or len(text.strip()) == 0:
            return False
            
        code_patterns = [
            r'def\s+\w+\s*\(', r'class\s+\w+', r'function\s+\w+\s*\(',
            r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'var\s+\w+\s*=',
            r'import\s+[\w\{\}\s,]+from', r'#include\s+<', r'public\s+class\s+',
            r'return\s+[^;]+;', r'if\s*\([^)]+\)\s*\{', r'for\s*\([^)]+\)'
        ]
        
        match_count = sum(1 for pat in code_patterns if re.search(pat, text))
        return match_count >= 1
