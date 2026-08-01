import re
from typing import Dict, Any, Tuple

# Domain Constants
DOMAIN_AUTO = "AUTO"
DOMAIN_WORK = "WORK"
DOMAIN_PERSONAL = "PERSONAL"
DOMAIN_DEVELOPMENT = "DEVELOPMENT"
DOMAIN_PROMPT_ENG = "PROMPT_ENGINEERING"
DOMAIN_GENERAL = "GENERAL"


class GraphSwitcher:
    """
    Universal Multi-Graph Context Switcher.
    Resolves the active Graph Domain (WORK, PERSONAL, DEVELOPMENT, PROMPT_ENGINEERING)
    based on user manual selection or automatic context detection.
    """

    @staticmethod
    def resolve_domain(context: Dict[str, Any], user_override: str = None) -> Tuple[str, str]:
        """
        Returns (domain_code, domain_description)
        """
        if user_override and user_override.upper() not in (DOMAIN_AUTO, ""):
            override_upper = user_override.upper()
            descriptions = {
                DOMAIN_WORK: "Work & Enterprise (Slack / Teams / Email)",
                DOMAIN_PERSONAL: "Personal & Casual (WhatsApp / Discord / Telegram)",
                DOMAIN_DEVELOPMENT: "Development & Engineering (IDE / GitHub)",
                DOMAIN_PROMPT_ENG: "AI Prompt Engineering (ChatGPT / Claude / Antigravity)",
                DOMAIN_GENERAL: "General Context"
            }
            return (override_upper, descriptions.get(override_upper, f"Domain: {override_upper}"))

        # Auto-detect domain from application context
        title = str(context.get("title", "")).lower()
        process = str(context.get("process", "")).lower()
        win_class = str(context.get("class", "")).lower()
        combined = f"{title} {process} {win_class}"

        # 1. AI Interfaces -> PROMPT_ENGINEERING Domain
        ai_kw = ["antigravity", "chatgpt", "claude", "cursor", "windsurf", "copilot", "openwebui", "lm-studio", "ollama", "perplexity"]
        if any(kw in combined for kw in ai_kw):
            return (DOMAIN_PROMPT_ENG, "AI Prompt Engineering Domain")

        # 2. Development Tools -> DEVELOPMENT Domain
        dev_procs = ["code.exe", "pycharm64.exe", "devenv.exe", "sublime_text.exe", "idea64.exe", "npp.exe"]
        dev_kw = ["github.com", "gitlab", "jira", "linear.app", "stack overflow"]
        if any(p in process for p in dev_procs) or any(kw in combined for kw in dev_kw):
            return (DOMAIN_DEVELOPMENT, "Development & Engineering Domain")

        # 3. Personal Chat -> PERSONAL Domain
        pers_procs = ["whatsapp.exe", "telegram.exe", "signal.exe", "discord.exe"]
        pers_kw = ["whatsapp", "web.whatsapp.com", "t.me", "telegram", "discord", "discord.com"]
        if any(p in process for p in pers_procs) or any(kw in combined for kw in pers_kw):
            return (DOMAIN_PERSONAL, "Personal & Casual Domain")

        # 4. Work Tools -> WORK Domain
        work_procs = ["slack.exe", "teams.exe", "ms-teams.exe", "outlook.exe", "thunderbird.exe", "mattermost.exe"]
        work_kw = ["app.slack.com", "teams.microsoft.com", "mail.google.com", "gmail", "outlook.office.com", "confluence", "notion"]
        if any(p in process for p in work_procs) or any(kw in combined for kw in work_kw):
            return (DOMAIN_WORK, "Work & Enterprise Domain")

        # Default Fallback
        return (DOMAIN_GENERAL, "General Domain")
