import unittest
from src.context_detector import (
    ContextDetector,
    SCENARIO_AI_PROMPT,
    SCENARIO_PERSONAL_CHAT,
    SCENARIO_PROFESSIONAL_CHAT,
    SCENARIO_EMAIL,
    SCENARIO_GITHUB_ISSUE,
    SCENARIO_SOURCE_CODE,
    SCENARIO_GENERAL
)

class TestContextDetector(unittest.TestCase):

    def test_detect_ai_prompt_mode(self):
        context = {
            "title": "ChatGPT - New Conversation",
            "process": "chrome.exe",
            "class": "Chrome_WidgetWin_1"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "explain quantum computing")
        self.assertEqual(scenario, SCENARIO_AI_PROMPT)

    def test_detect_antigravity_ide(self):
        context = {
            "title": "System-Wide AI Copilot - Antigravity",
            "process": "antigravity.exe",
            "class": "Chrome_WidgetWin_1"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "build a python app")
        self.assertEqual(scenario, SCENARIO_AI_PROMPT)

    def test_detect_personal_chat(self):
        context = {
            "title": "WhatsApp",
            "process": "whatsapp.exe",
            "class": "ApplicationFrameWindow"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "hey bro lets catch up tonight haha")
        self.assertEqual(scenario, SCENARIO_PERSONAL_CHAT)

    def test_detect_professional_chat(self):
        context = {
            "title": "#general - Acme Corp - Slack",
            "process": "slack.exe",
            "class": "Chrome_WidgetWin_1"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "Please review the PR by 3pm.")
        self.assertEqual(scenario, SCENARIO_PROFESSIONAL_CHAT)

    def test_detect_email(self):
        context = {
            "title": "Inbox - user@company.com - Outlook",
            "process": "outlook.exe",
            "class": "rguidance"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "Dear team, following up on our meeting.")
        self.assertEqual(scenario, SCENARIO_EMAIL)

    def test_detect_github_issue(self):
        context = {
            "title": "Issue #42 · facebook/react · GitHub - Google Chrome",
            "process": "chrome.exe",
            "class": "Chrome_WidgetWin_1"
        }
        scenario, _ = ContextDetector.detect_scenario(context, "button click crashes app on mobile")
        self.assertEqual(scenario, SCENARIO_GITHUB_ISSUE)

    def test_detect_source_code(self):
        context = {
            "title": "main.py - VSCode",
            "process": "code.exe",
            "class": "Chrome_WidgetWin_1"
        }
        code_text = "def process_data(items):\n    return [x * 2 for x in items]"
        scenario, _ = ContextDetector.detect_scenario(context, code_text)
        self.assertEqual(scenario, SCENARIO_SOURCE_CODE)

if __name__ == "__main__":
    unittest.main()
