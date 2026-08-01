"""
Screen Vision & Region Capture Module for System-Wide AI Copilot.
Handles native screen region snapping, OCR pre-processing, and multimodal vision context extraction.
"""

import os
import sys
import logging
import ctypes
import time
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("ScreenVision")
logger.setLevel(logging.INFO)


class ScreenVisionEngine:
    """Provides native Windows screen capture and multimodal image preparation."""

    @staticmethod
    def capture_full_screen(output_path: str, max_dim: int = 1280) -> bool:
        """Captures the entire desktop display and downscales image for low token consumption."""
        try:
            from PIL import ImageGrab, Image
            img = ImageGrab.grab()
            
            w, h = img.size
            if max(w, h) > max_dim:
                ratio = max_dim / float(max(w, h))
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "PNG", optimize=True)
            return True
        except Exception as e:
            logger.warning(f"Full screen capture error: {e}")
            return False

    @staticmethod
    def capture_active_window(output_path: str) -> bool:
        """Captures foreground window using native Windows GDI API."""
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False

            # If foreground window is Copilot Chatbot / Pet UI, skip to actual background app in Z-order
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value.lower()
            if "ai chatbot assistant" in title or "copilot controls" in title or not title:
                next_hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT = 2
                while next_hwnd:
                    user32.GetWindowTextW(next_hwnd, buf, 512)
                    t_str = buf.value.lower()
                    if user32.IsWindowVisible(next_hwnd) and t_str and "ai chatbot" not in t_str and "copilot" not in t_str:
                        hwnd = next_hwnd
                        break
                    next_hwnd = user32.GetWindow(next_hwnd, 2)

            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

            width = rect.right - rect.left
            height = rect.bottom - rect.top

            if width <= 0 or height <= 0:
                return False

            # GDI Capture logic using PIL if available, or GDI32 DIB
            try:
                from PIL import ImageGrab
                bbox = (rect.left, rect.top, rect.right, rect.bottom)
                img = ImageGrab.grab(bbox=bbox)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                img.save(output_path, "PNG")
                return True
            except Exception as e:
                logger.warning(f"PIL capture fallback error: {e}")

            return False
        except Exception as e:
            logger.error(f"Failed to capture window screenshot: {e}")
            return False

    @staticmethod
    def capture_full_screen(output_path: str) -> bool:
        """Captures entire virtual desktop screen."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "PNG")
            return True
        except Exception as e:
            logger.error(f"Failed to capture full screen: {e}")
            return False

    @staticmethod
    def prepare_multimodal_vision_payload(image_path: str) -> Optional[Dict[str, Any]]:
        """Prepares image payload for multimodal LLM processing."""
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            import base64
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            b64_data = base64.b64encode(img_bytes).decode("utf-8")
            return {
                "path": image_path,
                "mime_type": "image/png",
                "base64": b64_data,
                "size_bytes": len(img_bytes)
            }
        except Exception as e:
            logger.error(f"Failed to prepare vision payload: {e}")
            return None
