import os
import re
import json
import time
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import config


class LLMClient:
    """
    Provider-agnostic LLM Client supporting Multimodal Image Vision & Fast Text completion.
    Compatible with Groq, OpenAI, Ollama, vLLM, DeepSeek, etc.
    """

    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.base_url = config.LLM_BASE_URL.rstrip('/')
        self.model = config.LLM_MODEL
        self.timeout = config.TIMEOUT_SECONDS
        self.max_retries = config.MAX_RETRIES

    def generate_rewrite(
        self,
        system_prompt: str,
        user_prompt: str,
        image_path: Optional[str] = None,
        image_mime: str = "image/png"
    ) -> Dict[str, Any]:
        """
        Sends system + user prompt (and optional base64 image) to OpenAI-compatible endpoint.
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) System-Wide-AI-Copilot/1.0"
        }

        # Handle Image Input for Multimodal Vision
        selected_model = self.model
        user_content: Any = user_prompt

        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                image_mime = "image/png"
                if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
                    image_mime = "image/jpeg"

                # Use configured model (qwen/qwen3.6-27b) for multimodal vision queries
                selected_model = self.model

                user_content = [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{b64_data}"
                        }
                    }
                ]
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to load image {image_path}: {e}\n")

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
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
                
                # Handle 429 Rate Limit: If multimodal image was attached, strip image and fallback to pure text model
                if e.code == 429:
                    error_msg = "Rate limit reached (429). Retrying..."
                    if isinstance(payload.get("messages", [{}])[-1].get("content"), list):
                        # Strip base64 image and retry with pure text prompt on fast text model
                        payload["messages"][-1]["content"] = user_prompt
                        payload["model"] = "llama-3.3-70b-versatile"
                        data_bytes = json.dumps(payload).encode("utf-8")
                        time.sleep(1.0)
                        continue
                    elif attempt < self.max_retries:
                        time.sleep(2.0)
                        continue
                    else:
                        return {"success": False, "rewritten_text": "", "error": "Groq API rate limit exceeded (429). Please wait a few seconds."}

                if e.code in (400, 404) and "model" in err_body.lower():
                    # Fallback to fast standard model if specified model fails
                    if selected_model != "llama-3.3-70b-versatile":
                        selected_model = "llama-3.3-70b-versatile"
                        payload["model"] = selected_model
                        data_bytes = json.dumps(payload).encode("utf-8")
                        time.sleep(0.2)
                        continue
                    error_msg += f" (Model '{selected_model}' not found on Groq)"
                
                if attempt < self.max_retries:
                    time.sleep(0.5)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}


            except urllib.error.URLError as e:
                error_msg = f"Network Error: {e.reason}"
                if attempt < self.max_retries:
                    time.sleep(0.3)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}

            except Exception as e:
                error_msg = f"Unexpected Error: {str(e)}"
                if attempt < self.max_retries:
                    time.sleep(0.3)
                    continue
                return {"success": False, "rewritten_text": "", "error": error_msg}

        return {"success": False, "rewritten_text": "", "error": "Maximum retries reached."}

    def _clean_llm_output(self, text: str) -> str:
        text = text.strip()
        # Strip Qwen / DeepSeek reasoning think blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

        # Strip common meta preambles and introductory commentary
        meta_preambles = [
            r'^(Here is (the|your) (rewritten|refined|optimized|enhanced) (text|message|prompt|email|code)[:\s]*)',
            r'^(Here is a (rewritten|refined|optimized|enhanced) version[:\s]*)',
            r'^(Rewritten (text|message|prompt|email)[:\s]*)',
            r'^(Refined (text|message|prompt|email)[:\s]*)',
            r'^(#+\s+(Refined|Rewritten|Optimized|Result|Output)\s*(Text|Message|Prompt|Code)?[:\s]*\n+)'
        ]
        for pat in meta_preambles:
            text = re.sub(pat, '', text, flags=re.IGNORECASE).strip()

        # Strip markdown code fences ONLY if the entire output was wrapped in ``` without specific code context
        if text.startswith("```") and text.endswith("```") and text.count("```") == 2:
            lines = text.splitlines()
            if len(lines) >= 2 and not lines[0].strip().startswith("```"):
                text = "\n".join(lines[1:-1]).strip()

        # Strip leading/trailing surrounding quotes if present
        if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
            text = text[1:-1].strip()

        # Decode raw unicode escape sequences: \u0027 -> ', \u2019 -> ', etc.
        text = re.sub(
            r'\\u([0-9a-fA-F]{4})',
            lambda m: chr(int(m.group(1), 16)),
            text
        )
        return text
