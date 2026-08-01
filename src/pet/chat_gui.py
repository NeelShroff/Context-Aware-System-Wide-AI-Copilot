"""
Single Unified Cyber HUD AI Companion Chat Window (PyQt5).
Provides interactive multi-turn chat with automatic intent detection (screen vision, past work memory, code).
Includes click-outside auto-dismiss, Orbitron HUD typography, and one-click quick chips.
"""

import sys
import json
import time
import logging
import urllib.request
from PyQt5.QtCore import Qt, QTimer, QEvent, pyqtSignal, QThread
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QApplication
)

logger = logging.getLogger("CopilotChatWindow")
logger.setLevel(logging.INFO)


class ChatWorkerThread(QThread):
    """Background worker thread to execute /api/chat/unified HTTP request without freezing GUI."""
    response_received = pyqtSignal(dict)

    def __init__(self, user_msg: str, active_ctx: dict):
        super().__init__()
        self.user_msg = user_msg
        self.active_ctx = active_ctx

    def run(self):
        try:
            payload = json.dumps({
                "message": self.user_msg,
                "context": self.active_ctx
            }).encode("utf-8")

            req = urllib.request.Request(
                "http://127.0.0.1:8799/api/chat/unified",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            res = urllib.request.urlopen(req, timeout=25)
            data = json.loads(res.read().decode("utf-8"))
            self.response_received.emit(data)
        except Exception as e:
            self.response_received.emit({
                "success": False,
                "reply": f"Error communicating with AI engine: {str(e)}"
            })


def clean_chatbot_text_for_speech(text: str) -> str:
    """Strips HTML tags, markdown syntax (```code```, **, ##), and code blocks for clean speech audio."""
    if not text:
        return ""
    import re
    # Remove code blocks ```...```
    cleaned = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code `...`
    cleaned = re.sub(r'`[^`]+`', '', cleaned)
    # Remove HTML tags <...>
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Remove Markdown headings, bold, italic
    cleaned = re.sub(r'[\#\*\_\~\>]', '', cleaned)
    # Collapse multiple whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def markdown_to_html(text: str) -> str:
    """Converts Markdown syntax (**bold**, ### heading, * lists, `code`, > quotes) to clean HTML for PyQt5 QLabel."""
    if not text:
        return ""

    import re
    # Escape HTML special characters
    html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Code blocks ```code```
    html = re.sub(r'```(\w+)?\n?(.*?)```', r'<pre style="background:#080e1a; border:1px solid #38bdf8; padding:8px; border-radius:6px; font-family:monospace; color:#38bdf8;">\2</pre>', html, flags=re.DOTALL)

    # Inline code `code`
    html = re.sub(r'`([^`]+)`', r'<code style="background:#1e293b; color:#38bdf8; padding:2px 5px; border-radius:4px; font-family:monospace;">\1</code>', html)

    # Headings ### -> <h3>, ## -> <h2>, # -> <h1>
    html = re.sub(r'^###\s+(.*$)', r'<h3 style="color:#38bdf8; margin:6px 0 2px 0; font-size:12px; font-weight:700;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.*$)', r'<h2 style="color:#38bdf8; margin:8px 0 3px 0; font-size:13px; font-weight:700;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.*$)', r'<h1 style="color:#38bdf8; margin:10px 0 4px 0; font-size:14px; font-weight:700;">\1</h1>', html, flags=re.MULTILINE)

    # Bold **text** or __text__
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
    html = re.sub(r'__(.*?)__', r'<b>\1</b>', html)

    # Italic *text* or _text_
    html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html)

    # Blockquotes &gt; text
    html = re.sub(r'^&gt;\s+(.*$)', r'<blockquote style="border-left:3px solid #38bdf8; padding-left:8px; color:#94a3b8; margin:4px 0;">\1</blockquote>', html, flags=re.MULTILINE)

    # Bullet lists * item or - item
    html = re.sub(r'^\s*[\*\-]\s+(.*$)', r'&nbsp;&nbsp;• \1', html, flags=re.MULTILINE)

    # Convert newlines to <br>
    html = html.replace('\n', '<br>')
    return html


class CopilotChatWindow(QWidget):
    """
    Floating, Cyber HUD AI Companion Chatbot Modal Window.
    Stays on top, supports click-outside auto-close, and connects to AutonomousChatEngine.
    """

    def __init__(self, pet_window=None):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pet_window = pet_window
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(520)
        self.resize(520, 680)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget#panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1527, stop:1 #070c16);
                border: 1.5px solid rgba(56, 189, 248, 0.45);
                border-radius: 14px;
            }
            QLabel#title {
                color: #38bdf8;
                font-family: 'Orbitron', 'Share Tech Mono', 'Rajdhani', monospace, sans-serif;
                font-size: 11.5px;
                font-weight: 700;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            }
            QPushButton#close_btn {
                background: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 5px;
                padding: 3px 9px;
                font-family: 'Orbitron', monospace, sans-serif;
                font-size: 9.5px;
                font-weight: 700;
            }
            QPushButton#close_btn:hover {
                background: #ef4444;
                color: #ffffff;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QLineEdit#input_field {
                background: #131c31;
                color: #f8fafc;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 9px 14px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 12px;
            }
            QLineEdit#input_field:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton#send_btn {
                background: #38bdf8;
                color: #070c16;
                border: none;
                border-radius: 8px;
                padding: 9px 16px;
                font-family: 'Orbitron', monospace, sans-serif;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton#send_btn:hover {
                background: #7dd3fc;
            }
            QPushButton#mic_btn {
                background: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton#mic_btn:hover {
                background: #38bdf8;
                color: #070c16;
            }
            QPushButton#speak_btn {
                background: transparent;
                color: #38bdf8;
                border: none;
                font-size: 12px;
                padding: 2px 4px;
            }
            QPushButton#speak_btn:hover {
                color: #ffffff;
            }
            QPushButton#chip_btn {
                background: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 12px;
                padding: 5px 12px;
                font-family: 'Orbitron', monospace, sans-serif;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton#chip_btn:hover {
                background: rgba(56, 189, 248, 0.3);
                color: #ffffff;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame(self)
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header Row
        header = QHBoxLayout()
        title = QLabel("AI CHATBOT ASSISTANT")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("CLOSE")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedHeight(22)
        close_btn.clicked.connect(self.hide_chat)
        header.addWidget(close_btn)
        layout.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(56,189,248,0.7), stop:1 rgba(56,189,248,0.05)); height: 1px; border: none;")
        layout.addWidget(divider)

        # Scrollable Chat History Stream
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 4, 4, 4)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_content)
        layout.addWidget(self.scroll)

        # Welcome message
        self.add_message("bot", "Hello! I am your AI Companion. Ask me anything, summarize your screen, or query past work history!")

        # Quick Action Chips Row
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)

        chip_screen = QPushButton("Summarize Screen")
        chip_screen.setObjectName("chip_btn")
        chip_screen.clicked.connect(lambda: self._send_user_message("Summarize my current screen"))
        chips_layout.addWidget(chip_screen)

        chip_past = QPushButton("Past Work")
        chip_past.setObjectName("chip_btn")
        chip_past.clicked.connect(lambda: self._send_user_message("What did I work on earlier today?"))
        chips_layout.addWidget(chip_past)

        chip_reply = QPushButton("Draft Reply")
        chip_reply.setObjectName("chip_btn")
        chip_reply.clicked.connect(lambda: self._send_user_message("Help me draft a reply to this message"))
        chips_layout.addWidget(chip_reply)

        layout.addLayout(chips_layout)

        # Input Row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Ask AI anything...")
        self.input_field.returnPressed.connect(self._on_send_click)
        input_layout.addWidget(self.input_field)

        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setToolTip("Voice Dictation (Click to Speak)")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.clicked.connect(self._trigger_voice_input)
        input_layout.addWidget(self.mic_btn)

        self.send_btn = QPushButton("SEND")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedHeight(36)
        self.send_btn.clicked.connect(self._on_send_click)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)
        outer.addWidget(panel)

    def add_message(self, sender: str, text: str):
        """Adds a speech message bubble to the chat stream with rich HTML markdown formatting and voice readout support."""
        msg_box = QFrame()
        msg_layout = QVBoxLayout(msg_box)
        msg_layout.setContentsMargins(12, 10, 12, 10)

        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if sender == "user":
            lbl.setText(text)
            msg_box.setStyleSheet("""
                QFrame {
                    background: rgba(56, 189, 248, 0.18);
                    border: 1px solid rgba(56, 189, 248, 0.4);
                    border-radius: 10px;
                    margin-left: 50px;
                }
                QLabel {
                    color: #38bdf8;
                    font-family: 'Segoe UI', 'Inter', sans-serif;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
        else:
            html_text = markdown_to_html(text)
            lbl.setTextFormat(Qt.RichText)
            lbl.setText(html_text)
            msg_box.setStyleSheet("""
                QFrame {
                    background: #131c31;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 10px;
                    margin-right: 35px;
                }
                QLabel {
                    color: #f8fafc;
                    font-family: 'Segoe UI', 'Inter', sans-serif;
                    font-size: 12px;
                    line-height: 1.5;
                }
            """)

            # Add speaker button for bot response playback
            if text != "Thinking...":
                bot_header = QHBoxLayout()
                speak_btn = QPushButton("🔊 Listen")
                speak_btn.setObjectName("speak_btn")
                speak_btn.setCursor(Qt.PointingHandCursor)
                clean_speech = clean_chatbot_text_for_speech(text)
                speak_btn.clicked.connect(lambda _, s=clean_speech: self._speak_bot_text(s))
                bot_header.addStretch()
                bot_header.addWidget(speak_btn)
                msg_layout.addLayout(bot_header)

        msg_layout.addWidget(lbl)
        
        # Remove stretch before adding new item, then add stretch back
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, msg_box)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def _speak_bot_text(self, speech_text: str):
        if not speech_text:
            return
        try:
            from src.tts_engine import announce_speech_bubble
            announce_speech_bubble(speech_text)
        except Exception as e:
            logger.warning(f"Voice playback error: {e}")

    def _trigger_voice_input(self):
        self.input_field.setPlaceholderText("🎙️ Listening... Speak now...")
        QApplication.processEvents()
        try:
            from src.voice_capture import dictate_to_text
            res = dictate_to_text(max_seconds=8.0)
            if res.get("success") and res.get("text"):
                spoken_text = res.get("text")
                self.input_field.setText(spoken_text)
                self._on_send_click()
            else:
                self.input_field.setPlaceholderText("Ask AI anything...")
        except Exception as e:
            logger.warning(f"Voice dictation error: {e}")
            self.input_field.setPlaceholderText("Ask AI anything...")

    def _on_send_click(self):
        msg = self.input_field.text().strip()
        if not msg:
            return
        self.input_field.clear()
        self._send_user_message(msg)

    def _send_user_message(self, msg: str):
        self.add_message("user", msg)
        self.add_message("bot", "Thinking...")

        screen_keywords = ["screen", "look at", "what am i looking at", "summarize screen", "this window", "this page", "this file"]
        is_screen_query = any(kw in msg.lower() for kw in screen_keywords)

        if is_screen_query:
            self.hide()
            QApplication.processEvents()
            time.sleep(0.08)

        active_ctx = {
            "process": "Desktop",
            "title": "Desktop Context"
        }

        # Start background worker thread
        self._worker = ChatWorkerThread(msg, active_ctx)
        self._worker.response_received.connect(self._on_bot_response)
        self._worker.start()

        if is_screen_query:
            QTimer.singleShot(150, self.show)

    def _on_bot_response(self, res: dict):
        # Remove the temporary "Thinking..." placeholder
        count = self.chat_layout.count()
        if count > 1:
            item = self.chat_layout.itemAt(count - 2)
            if item and item.widget():
                w = item.widget()
                self.chat_layout.removeWidget(w)
                w.deleteLater()

        reply = res.get("reply", "No response generated.")
        self.add_message("bot", reply)

        # Trigger character voice readout for chatbot response
        try:
            from src.tts_engine import announce_speech_bubble
            clean_speech = clean_chatbot_text_for_speech(reply)
            if clean_speech:
                announce_speech_bubble(clean_speech)
        except Exception as e:
            logger.warning(f"Chatbot voice readout error: {e}")

    def show_beside_pet(self):
        """Position chat window beside 3D pet dynamically."""
        screen = QApplication.primaryScreen().availableGeometry()
        panel_w = min(580, max(460, int(screen.width() * 0.32)))
        panel_h = min(720, max(520, screen.height() - 60))
        self.setFixedSize(panel_w, panel_h)

        if self.pet_window:
            pet_x = self.pet_window.x()
            pet_y = self.pet_window.y()
            pet_w = self.pet_window.width()
            x = pet_x - panel_w - 10
            if x < screen.x():
                x = pet_x + pet_w + 10
            y = min(pet_y, screen.y() + screen.height() - panel_h - 10)
        else:
            x = screen.x() + screen.width() - panel_w - 20
            y = screen.y() + screen.height() - panel_h - 40

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def hide_chat(self):
        self.hide()

    def changeEvent(self, event):
        """Auto-close chat panel when user clicks outside."""
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide_chat()
        super().changeEvent(event)
