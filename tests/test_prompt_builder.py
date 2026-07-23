import unittest
from src.prompt_builder import PromptBuilder
from src.context_detector import SCENARIO_AI_PROMPT, SCENARIO_PERSONAL_CHAT

class TestPromptBuilder(unittest.TestCase):

    def test_prompt_engineering_mode_instructions(self):
        context = {"title": "Claude", "process": "chrome.exe"}
        sys_prompt, user_prompt = PromptBuilder.build_prompts(
            SCENARIO_AI_PROMPT, "AI Prompt Interface", context, "write a script"
        )
        self.assertIn("AI PROMPT ENGINEERING MODE", sys_prompt)
        self.assertIn("write a script", user_prompt)

    def test_personal_chat_instructions(self):
        context = {"title": "WhatsApp", "process": "whatsapp.exe"}
        sys_prompt, user_prompt = PromptBuilder.build_prompts(
            SCENARIO_PERSONAL_CHAT, "WhatsApp", context, "hey bro"
        )
        self.assertIn("PERSONAL MESSAGING", sys_prompt)
        self.assertIn("DO NOT make the message sound corporate", sys_prompt)

if __name__ == "__main__":
    unittest.main()
