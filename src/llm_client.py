import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from src.config import config

class LLMClient:
    """
    Provider-agnostic LLM Client using OpenAI-compatible HTTP REST API calls.
    Supports Groq, OpenAI, Ollama, vLLM, DeepSeek, etc.
    """

    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.base_url = config.LLM_BASE_URL.rstrip('/')
        self.model = config.LLM_MODEL
        self.timeout = config.TIMEOUT_SECONDS
        self.max_retries = config.MAX_RETRIES

    def generate_rewrite(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Sends system + user prompt to the OpenAI-compatible endpoint.
        Returns dict with:
        {
            "success": True/False,
            "rewritten_text": str,
            "error": str or None
        }
        """
        if not self.api_key or self.api_key == "your_groq_api_key_here":
            return {
                "success": False,
                "rewritten_text": "",
                "error": "GROQ_API_KEY not configured in .env"
            }

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "System-Wide-AI-Copilot/1.0 (Windows)"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    res_body = response.read().decode("utf-8")
                    res_json = json.loads(res_body)
                    
                    choices = res_json.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        # Clean potential wrapping markdown quotes if model added them despite instructions
                        cleaned_content = self._clean_llm_output(content)
                        return {
                            "success": True,
                            "rewritten_text": cleaned_content,
                            "error": None
                        }
                    else:
                        return {
                            "success": False,
                            "rewritten_text": "",
                            "error": "LLM response contained no completion choices."
                        }

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8") if e.fp else str(e)
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                # If model not found error on Groq, provide helpful tip
                if e.code == 404 and "model" in err_body.lower():
                    error_msg += f" (Model '{self.model}' may not be available on Groq)"
                
                if attempt < self.max_retries:
                    time.sleep(0.5)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}

            except urllib.error.URLError as e:
                error_msg = f"Network Error: {e.reason}"
                if attempt < self.max_retries:
                    time.sleep(0.5)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}

            except Exception as e:
                error_msg = f"Unexpected Error: {str(e)}"
                if attempt < self.max_retries:
                    time.sleep(0.5)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}

        return {"success": False, "rewritten_text": "", "error": "Maximum retries reached."}

    def _clean_llm_output(self, text: str) -> str:
        """Removes accidental leading/trailing preambles or code fences if raw text was returned."""
        text = text.strip()
        # If output was wrapped in triple backticks block without language or md, unwrap if it matches original text format
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                # Remove first and last lines
                return "\n".join(lines[1:-1]).strip()
        return text
