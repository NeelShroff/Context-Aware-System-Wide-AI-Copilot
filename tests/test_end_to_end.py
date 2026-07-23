import json
import unittest
from unittest.mock import patch
from src.main import process_request
from src.context_detector import SCENARIO_AI_PROMPT, SCENARIO_PERSONAL_CHAT, SCENARIO_GITHUB_ISSUE

class TestEndToEndProcess(unittest.TestCase):

    @patch("src.llm_client.LLMClient.generate_rewrite")
    def test_ai_prompt_engineering_flow(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "rewritten_text": "### Objective\nCreate a Python script for web scraping.\n\n### Constraints\n- Use BeautifulSoup or Playwright\n- Include error handling",
            "error": None
        }

        input_data = {
            "text": "make a python script for web scraping",
            "context": {
                "title": "ChatGPT - Google Chrome",
                "process": "chrome.exe"
            }
        }

        res = process_request(input_data)

        self.assertTrue(res["success"])
        self.assertEqual(res["scenario"], SCENARIO_AI_PROMPT)
        self.assertTrue(res["changed"])
        self.assertIn("Objective", res["rewritten_text"])

    @patch("src.llm_client.LLMClient.generate_rewrite")
    def test_whatsapp_casual_flow(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "rewritten_text": "hey bro, let's grab lunch tomorrow!",
            "error": None
        }

        input_data = {
            "text": "hey bro lets grab lunch tmrw",
            "context": {
                "title": "WhatsApp",
                "process": "whatsapp.exe"
            }
        }

        res = process_request(input_data)

        self.assertTrue(res["success"])
        self.assertEqual(res["scenario"], SCENARIO_PERSONAL_CHAT)
        self.assertIn("lunch tomorrow", res["rewritten_text"])

    @patch("src.llm_client.LLMClient.generate_rewrite")
    def test_github_bug_report_flow(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "rewritten_text": "### Summary\nClicking submit button crashes application on Android.\n\n### Steps to Reproduce\n1. Open app\n2. Click submit",
            "error": None
        }

        input_data = {
            "text": "submit button crashes app on android",
            "context": {
                "title": "Issues · owner/repo · GitHub",
                "process": "msedge.exe"
            }
        }

        res = process_request(input_data)

        self.assertTrue(res["success"])
        self.assertEqual(res["scenario"], SCENARIO_GITHUB_ISSUE)
        self.assertIn("Summary", res["rewritten_text"])

if __name__ == "__main__":
    unittest.main()
