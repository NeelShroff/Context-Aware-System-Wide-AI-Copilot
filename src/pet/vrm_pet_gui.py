"""
3D VRM / WebGL PyQt5 Desktop Pet Transparent Window Launcher.
Hosts the WebGL 3D avatar layer with glassmorphism overlays on Windows.
Features autonomous full-screen wandering, dragging, and character model selection.
Right-click opens a native Qt Control Panel (separate window - zero Chromium interference).
"""

import os
import sys
import logging
import time
import random

# QtWebEngine Environment Settings (GPU Rasterization & Hardware Acceleration)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist --enable-features=UseSkiaRenderer --disable-gpu-driver-bug-workarounds"

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import shutil
import webbrowser
from PyQt5.QtCore import Qt, QPoint, QUrl, QTimer, QEvent
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QFileDialog, QMessageBox, QInputDialog
)
from PyQt5.QtGui import QColor, QCursor, QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings

from src.pet.pet_bridge import start_pet_server, update_pet_state, get_pet_state, PET_STATE

logger = logging.getLogger("VRMPetGUI")
logger.setLevel(logging.INFO)


class TransparentWebPage(QWebEnginePage):
    """Custom WebEnginePage with transparent background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor(QColor(0, 0, 0, 0))


# ==============================================================================
# Native Qt Control Panel (Zero Chromium Interference)
# ==============================================================================
class CopilotControlPanel(QWidget):
    """Standalone Qt Widget Control Panel - opens beside the 3D pet on right-click.
    Completely separate from Chromium's event loop. Stays open until user closes it."""

    DARK_BG = "#080e1a"
    PANEL_BG = "#0f172a"
    BORDER_CYAN = "rgba(56, 189, 248, 0.45)"
    TEXT_MAIN = "#e2e8f0"
    HEADER_CYAN = "#38bdf8"
    SECTION_TEXT = "#38bdf8"
    CARD_BG = "#131c31"
    CARD_HOVER_BG = "#1e293b"
    CARD_BORDER = "rgba(56, 189, 248, 0.2)"
    CARD_HOVER_BORDER = "#38bdf8"
    DANGER = "#ef4444"

    def __init__(self, pet_window):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pet_window = pet_window
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(330)
        self.setFixedWidth(330)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            QWidget#panel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1527, stop:1 #070c16);
                border: 1.5px solid {self.BORDER_CYAN};
                border-radius: 12px;
            }}
            QLabel#title {{
                color: {self.HEADER_CYAN};
                font-family: 'Orbitron', 'Share Tech Mono', 'Rajdhani', 'Cascadia Code', 'Consolas', monospace, sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.6px;
                text-transform: uppercase;
            }}
            QLabel#section {{
                color: {self.SECTION_TEXT};
                font-family: 'Orbitron', 'Share Tech Mono', 'Rajdhani', 'Cascadia Code', 'Consolas', monospace, sans-serif;
                font-size: 9.5px;
                font-weight: 700;
                letter-spacing: 1.2px;
                text-transform: uppercase;
                padding: 10px 0 4px 2px;
            }}
            QPushButton#card {{
                background: {self.CARD_BG};
                color: {self.TEXT_MAIN};
                border: 1px solid {self.CARD_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Orbitron', 'Share Tech Mono', 'Rajdhani', 'Cascadia Code', 'Consolas', monospace, sans-serif;
                font-size: 10.5px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-align: left;
            }}
            QPushButton#card:hover {{
                background: {self.CARD_HOVER_BG};
                border: 1px solid {self.CARD_HOVER_BORDER};
                color: #38bdf8;
            }}
            QPushButton#close_btn {{
                background: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 5px;
                padding: 3px 9px;
                font-family: 'Orbitron', 'Share Tech Mono', 'Rajdhani', 'Cascadia Code', 'Consolas', monospace, sans-serif;
                font-size: 9.5px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton#close_btn:hover {{
                background: {self.DANGER};
                color: #ffffff;
                border: 1px solid {self.DANGER};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 5px;
                margin: 2px 0 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(56, 189, 248, 0.4);
                min-height: 25px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(56, 189, 248, 0.95);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame(self)
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        title = QLabel("COPILOT CONTROLS")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("CLOSE")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedHeight(23)
        close_btn.clicked.connect(self.hide_panel)
        header.addWidget(close_btn)
        layout.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(56,189,248,0.7), stop:1 rgba(56,189,248,0.05)); height: 1px; border: none;")
        layout.addWidget(divider)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 4, 2)
        content_layout.setSpacing(3)

        def section(text):
            lbl = QLabel(text)
            lbl.setObjectName("section")
            content_layout.addWidget(lbl)

        def card(label, callback):
            btn = QPushButton(label)
            btn.setObjectName("card")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(callback)
            content_layout.addWidget(btn)
            return btn

        # AI Assistant Chatbot
        section("AI ASSISTANT")
        card("Open AI Chatbot (Ctrl+Alt+C)", self._open_chat)

        # Workspace Context
        section("WORKSPACE CONTEXT")
        self.app_label_btn = card("Active: Desktop", self._show_active_context)
        card("Search Workspaces (Ctrl+Shift+P)", self._search_workspaces)

        # Domain
        section("DOMAIN SCENARIOS")
        card("Auto-Detect Domain (Smart)", lambda: self._set_domain("AUTO"))
        card("Work & Enterprise", lambda: self._set_domain("WORK"))
        card("Personal & Casual", lambda: self._set_domain("PERSONAL"))
        card("Development & Tech", lambda: self._set_domain("DEVELOPMENT"))
        card("AI Prompt Engineering", lambda: self._set_domain("PROMPT_ENGINEERING"))

        # AI Dashboards
        section("DASHBOARDS & KNOWLEDGE")
        card("View Knowledge Graph", self._open_knowledge_graph)

        # Spider-Man Costume Suits Selector
        section("SPIDER-MAN SUITS")
        card("[01] Classic Red & Blue", lambda: self._switch_char("01 [Default]"))
        card("[02] Crimson Red Suit", lambda: self._switch_char("02 [Red]"))
        card("[03] Orange Suit", lambda: self._switch_char("03 [Orange]"))
        card("[04] Yellow Suit", lambda: self._switch_char("04 [Yellow]"))
        card("[05] Collab Rivals Suit", lambda: self._switch_char("05 [Collab - Rivals]"))
        card("[06] Symbiote Black Suit", lambda: self._switch_char("06 [Black - Black Suit]"))
        card("[07] Negative Zone White", lambda: self._switch_char("07 [White - Negative Suit]"))
        card("[08] Cobalt Electroproof", lambda: self._switch_char("08 [Cobalt - Electroproof]"))
        card("[09] Iron Spider Gold", lambda: self._switch_char("09 [Gold - Iron Spidey]"))

        # Interactive Spider Actions
        section("ACTION TRIGGERS")
        card("Shoot Web Blast", lambda: self._speech("Web Shoot"))
        card("Spider-Sense Alert", lambda: update_pet_state({"pet_mode": "THINKING"}))
        card("Rest / Sleep Stance", lambda: self._trigger_sleep_mode())

        # Startup & Launch Controls
        section("STARTUP & LAUNCH SETTINGS")
        self.autostart_btn = card("Auto-Start on Boot: Checking...", self._toggle_autostart)
        card("Re-create Desktop Shortcut", self._create_desktop_shortcut)

        # Wandering Controls
        section("SYSTEM CONTROLS")
        self.wander_btn = card("Pause Screen Wandering", self._toggle_wander)
        card("Reset Window Position", self._reset_pos)
        card("Test Speech Bubble", self._test_speech)
        card("Hide 3D Companion", self.pet_window.hide)
        card("🛑 TURN OFF SYSTEM COPILOT", self._shutdown_entire_copilot)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        outer.addWidget(panel)

    def show_beside_pet(self):
        """Position panel beside the 3D pet adaptively based on active screen geometry and DPI."""
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Responsive scaling: calculate dynamic width and height based on screen dimensions
        panel_w = min(400, max(320, int(screen.width() * 0.22)))
        panel_h = min(580, max(380, screen.height() - 80))
        self.setFixedSize(panel_w, panel_h)

        pet_x = self.pet_window.x()
        pet_y = self.pet_window.y()
        pet_w = self.pet_window.width()

        # Place left of pet if there's room, else right
        x = pet_x - panel_w - 10
        if x < screen.x():
            x = pet_x + pet_w + 10

        # Keep inside screen bounds
        if x + panel_w > screen.x() + screen.width():
            x = screen.x() + screen.width() - panel_w - 10
        if x < screen.x():
            x = screen.x() + 10

        y = pet_y
        if y + panel_h > screen.y() + screen.height():
            y = screen.y() + screen.height() - panel_h - 10
        if y < screen.y():
            y = screen.y() + 10

        self.move(x, y)

        # Update active app label
        active_app = PET_STATE.get("active_app", "Desktop")
        short = active_app[:20] + "..." if len(active_app) > 20 else active_app
        self.app_label_btn.setText(f"Active: {short}")
        wander_label = "Pause Screen Wandering" if self.pet_window.is_wandering else "Resume Screen Wandering"
        self.wander_btn.setText(wander_label)

        # Update Auto-Start Status Button
        try:
            from scripts.manage_startup import is_autostart_enabled
            enabled = is_autostart_enabled()
            self.autostart_btn.setText(f"Auto-Start on Boot: {'ENABLED' if enabled else 'DISABLED'}")
        except Exception:
            self.autostart_btn.setText("Auto-Start on Boot: Toggle")

        self.show()
        self.raise_()
        self.activateWindow()

    def hide_panel(self):
        self.hide()

    def changeEvent(self, event):
        """Auto-close control panel when user clicks outside on desktop or another window."""
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide_panel()
        super().changeEvent(event)

    def _open_chat(self):
        self.hide_panel()
        self.pet_window.open_chat_window()

    def _speech(self, text):
        update_pet_state({"speech_text": text, "speech_duration": 3.0, "speech_timestamp": time.time(), "pet_mode": "TALKING"})

    def _set_domain(self, domain):
        update_pet_state({"domain_category": domain})
        self._speech(f"Domain: {domain}")

    def _switch_char(self, style):
        self.pet_window.set_character_style(style)
        self.hide_panel()

    def _toggle_wander(self):
        self.pet_window.toggle_wandering()
        label = "Pause Screen Wandering" if self.pet_window.is_wandering else "Resume Screen Wandering"
        self.wander_btn.setText(label)

    def _reset_pos(self):
        self.pet_window.reset_position()
        self.hide_panel()

    def _test_speech(self):
        self._speech("AI Copilot active and ready")

    def _open_knowledge_graph(self):
        """Launches local Neo4j Desktop application if installed and opens Neo4j Browser in web browser."""
        self.hide_panel()
        neo4j_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Neo4j Desktop\Neo4j Desktop.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Neo4j Desktop\Neo4j Desktop.exe"),
            r"C:\Program Files\Neo4j Desktop\Neo4j Desktop.exe",
        ]
        launched = False
        for p in neo4j_paths:
            if os.path.exists(p):
                try:
                    os.startfile(p)
                    launched = True
                    break
                except Exception as e:
                    logger.warning(f"Could not open Neo4j Desktop exe: {e}")

        webbrowser.open("http://localhost:7474")
        msg = "Opened Neo4j Desktop & Browser" if launched else "Opened Neo4j Browser (http://localhost:7474)"
        self._speech(msg)

    def _search_workspaces(self):
        """Opens interactive Qt input dialog to search/switch workspace context."""
        active_app = PET_STATE.get("active_app", "Desktop")
        text, ok = QInputDialog.getText(
            self,
            "Context Quick Search",
            "Search Workspaces or enter active Context name:",
            text=active_app
        )
        if ok and text.strip():
            new_context = text.strip()
            update_pet_state({"active_app": new_context})
            short = new_context[:20] + "..." if len(new_context) > 20 else new_context
            self.app_label_btn.setText(f"Active: {short}")
            self._speech(f"Workspace: {new_context}")

    def _show_active_context(self):
        """Displays current active workspace context status."""
        active_app = PET_STATE.get("active_app", "Desktop")
        domain = PET_STATE.get("domain_category", "AUTO")
        self._speech(f"Active: {active_app} [{domain}]")

    def _toggle_autostart(self):
        try:
            from scripts.manage_startup import is_autostart_enabled, set_autostart
            current = is_autostart_enabled()
            new_state = not current
            set_autostart(new_state)
            self.autostart_btn.setText(f"Auto-Start on Boot: {'ENABLED' if new_state else 'DISABLED'}")
            status_str = "ENABLED" if new_state else "DISABLED"
            self._speech(f"Auto-Start: {status_str}")
        except Exception as e:
            logger.error(f"Error toggling autostart: {e}")
            self._speech("Error toggling startup")

    def _create_desktop_shortcut(self):
        try:
            from scripts.manage_startup import create_shortcuts
            create_shortcuts()
            self._speech("Shortcut Created!")
        except Exception as e:
            logger.error(f"Error creating shortcuts: {e}")
            self._speech("Shortcut Error")

    def _shutdown_entire_copilot(self):
        try:
            import subprocess
            # Kill AutoHotkey engine background process
            subprocess.run(["taskkill", "/F", "/IM", "AutoHotkey64.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "AutoHotkey.exe"], capture_output=True)
        except Exception:
            pass
        QApplication.quit()


class VRMPetWindow(QMainWindow):
    """Frameless, transparent, always-on-top 3D Desktop Pet Window."""
    def __init__(self, ui_url: str):
        super().__init__()

        self.ui_url = ui_url
        self.drag_position = QPoint()

        # Window Flags & Attributes for Desktop Overlay
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        # Compact pet window setup with dynamic trajectory bounding box for web zips
        screen = QApplication.primaryScreen().availableGeometry()
        self.screen_x = screen.x()
        self.screen_y = screen.y()
        self.screen_w = screen.width()
        self.screen_h = screen.height()

        pos_x = self.screen_x + self.screen_w - 200
        pos_y = self.screen_y + self.screen_h - 240
        self.setGeometry(pos_x, pos_y, 180, 230)

        # Web Engine View Setup
        self.web_view = QWebEngineView(self)
        self.web_page = TransparentWebPage(self.web_view)
        self.web_view.setPage(self.web_page)

        # Hardware Acceleration Settings for 60 FPS GPU Canvas Rendering
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)

        self.web_view.setUrl(QUrl(self.ui_url))
        self.web_view.setContextMenuPolicy(Qt.NoContextMenu)

        # Install Event Filter for drag + right-click interception BEFORE Chromium
        self.web_view.installEventFilter(self)
        if self.web_view.focusProxy():
            self.web_view.focusProxy().installEventFilter(self)

        self.setCentralWidget(self.web_view)
        self.setWindowTitle("System-Wide AI Copilot 3D Pet")

        # Native Control Panel (separate Qt window)
        self.control_panel = CopilotControlPanel(self)
        from src.pet.chat_gui import CopilotChatWindow
        self.chat_window = CopilotChatWindow(self)

        # Attach focusProxy event filter once web view is ready
        QTimer.singleShot(500, self._attach_proxy_filter)

        # Full-Screen Autonomous Wandering Setup
        self.is_wandering = True
        self.pause_ticks = 0
        self.char_x = pos_x
        self.char_y = pos_y
        self.target_x = pos_x
        self.target_y = pos_y
        self.is_dragging = False
        self._is_zip_active = False

        self.wander_timer = QTimer(self)
        self.wander_timer.setTimerType(Qt.PreciseTimer)
        self.wander_timer.setInterval(16)  # High-precision 60 FPS timer
        self.wander_timer.timeout.connect(self._update_wander_position)
        self.wander_timer.start()

        self._pick_new_wander_target()

    def _attach_proxy_filter(self):
        proxy = self.web_view.focusProxy()
        if proxy:
            proxy.installEventFilter(self)

    # ==============================================================================
    # Event Filter — Intercept Right-Click & Drag BEFORE Chromium
    # ==============================================================================
    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.is_dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            elif event.button() == Qt.RightButton:
                # Intercept right-click here — before Chromium ever sees it
                QTimer.singleShot(0, self._toggle_control_panel)
                return True  # Swallow event completely
        elif event.type() == QEvent.MouseMove:
            if (event.buttons() & Qt.LeftButton) and self.is_dragging:
                self.move(event.globalPos() - self.drag_position)
                self.char_x = self.x()
                self.char_y = self.y()
                self.target_x = self.char_x
                self.target_y = self.char_y
        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                if not getattr(self, '_drag_moved', False):
                    self.trigger_interactive_web_shoot()
                self.is_dragging = False
                self._drag_moved = False
                self.pause_ticks = 60
        elif event.type() == QEvent.MouseButtonDblClick:
            return True  # Swallow double-click completely to prevent event flooding
        elif event.type() == QEvent.ContextMenu:
            return True  # Swallow Chromium context menu completely
        return super().eventFilter(source, event)

    def _trigger_sleep_mode(self):
        """Immediately trigger SLEEP mode, lock motion, and push direct state to companion."""
        import time
        self._sync_pet_state({
            "pet_mode": "SLEEP",
            "motion_state": "SLEEP",
            "is_moving": False,
            "web_anchor_x": None,
            "web_anchor_y": None,
            "char_rel_x": None,
            "char_rel_y": None,
            "speech_text": "Zzz... Web-sleeping...",
            "speech_duration": 6.0,
            "speech_timestamp": time.time()
        })

    def trigger_interactive_web_shoot(self):
        """Dynamic full-screen web trajectory with strict mutual exclusion constraint against web zipping."""
        if getattr(self, '_is_zip_active', False) or getattr(self, '_is_shoot_busy', False):
            return  # Constraint: Cannot shoot web while web zipping or actively shooting!

        import time
        now = time.time()
        if hasattr(self, '_last_shoot_time') and (now - self._last_shoot_time) < 0.6:
            return  # Swallow rapid double-click triggers
        self._last_shoot_time = now
        self._is_shoot_busy = True

        heading = getattr(self, '_heading_dir', 1)
        curr_x = self.char_x
        curr_y = self.char_y

        # Dynamic target extending all the way across the desktop screen in facing direction
        if heading >= 0:
            target_shoot_x = self.screen_x + self.screen_w - 220
        else:
            target_shoot_x = self.screen_x + 60

        target_shoot_y = max(self.screen_y + 60, min(curr_y - 40, self.screen_y + self.screen_h - 220))

        pad_l = 80
        pad_t = 80
        pad_r = 160
        pad_b = 160

        win_l = int(min(curr_x, target_shoot_x) - pad_l)
        win_t = int(min(curr_y, target_shoot_y) - pad_t)
        win_w = int(max(curr_x, target_shoot_x) - win_l + pad_r + 160)
        win_h = int(max(curr_y, target_shoot_y) - win_t + pad_b + 200)

        self.setGeometry(win_l, win_t, win_w, win_h)
        self._zip_win_l = win_l
        self._zip_win_t = win_t

        char_rel_x = (curr_x - win_l) + 80
        char_rel_y = (curr_y - win_t) + 110
        anchor_x = (target_shoot_x - win_l) + 80
        anchor_y = (target_shoot_y - win_t) + 80

        import math
        dist = math.sqrt((target_shoot_x - curr_x)**2 + (target_shoot_y - curr_y)**2)
        speed = max(14, min(24, dist / 35))
        flight_ms = int(((dist / speed) + 25) * 16.6)
        finish_delay = max(800, min(2400, flight_ms))

        self._sync_pet_state({
            "web_shoot_trigger": True,
            "char_rel_x": char_rel_x,
            "char_rel_y": char_rel_y,
            "web_anchor_x": anchor_x,
            "web_anchor_y": anchor_y,
            "motion_state": "IDLE"
        })
        QTimer.singleShot(100, lambda: update_pet_state({"web_shoot_trigger": False}))
        QTimer.singleShot(finish_delay, self._finish_web_shoot)

    def _finish_web_shoot(self):
        """Reset shoot busy flag and snap window back to compact box."""
        self._is_shoot_busy = False
        if not getattr(self, '_is_moving_zip', False):
            self.setGeometry(int(self.char_x), int(self.char_y), 160, 200)
            self._is_zip_active = False

    def _toggle_control_panel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide_panel()
        else:
            self.pause_ticks = 300  # Freeze wandering while panel is open
            self.control_panel.show_beside_pet()

    # ==============================================================================
    # Autonomous Full-Screen Wandering & Action Planner Engine
    # ==============================================================================
    def _pick_new_wander_target(self):
        margin = 40
        curr_x = self.char_x
        curr_y = self.char_y

        # Query active window coordinates via Win32 API
        app_x, app_y, app_w, app_h = None, None, None, None
        try:
            import ctypes, ctypes.wintypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                rect = ctypes.wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if w > 200 and h > 200:
                        app_x, app_y, app_w, app_h = rect.left, rect.top, w, h
        except Exception:
            pass

        state = get_pet_state()
        is_chat = state.get("is_chat_env", False)

        # Decide Action Mode: Relaxed PATROL (85%), Rare WEB_VERTICAL (7.5%), Rare WEB_DIAGONAL (7.5%)
        mode_choice = random.choices(["PATROL", "WEB_VERTICAL", "WEB_DIAGONAL"], weights=[0.85, 0.075, 0.075])[0]

        if app_x is not None and is_chat and random.random() < 0.7:
            # Leap right onto the top title bar of Chrome/Browser!
            self.target_x = max(self.screen_x + margin, min(app_x + app_w // 2 - 80, self.screen_x + self.screen_w - 160 - margin))
            self.target_y = max(self.screen_y + margin, min(app_y + 15, self.screen_y + self.screen_h - 200 - margin))
        elif mode_choice == "PATROL":
            # Strictly horizontal patrol along current Y surface (zero vertical drift)
            min_x = max(self.screen_x + margin, app_x + 20 if app_x else self.screen_x + margin)
            max_x = min(self.screen_x + self.screen_w - 160 - margin, (app_x + app_w - 180) if app_x else (self.screen_x + self.screen_w - 160 - margin))
            if max_x > min_x:
                self.target_x = random.randint(min_x, max_x)
            else:
                self.target_x = random.randint(self.screen_x + margin, self.screen_x + self.screen_w - 160 - margin)
            self.target_y = curr_y  # Keep Y strictly identical!
        elif mode_choice == "WEB_VERTICAL":
            # Strictly vertical zip UP to window top or DOWN to lower screen
            self.target_x = curr_x  # Keep X strictly identical!
            if curr_y > self.screen_y + 250:
                self.target_y = max(self.screen_y + margin, (app_y + 15) if app_y else (self.screen_y + 60))
            else:
                self.target_y = min(self.screen_y + self.screen_h - 200 - margin, (app_y + app_h - 220) if app_y else (self.screen_y + self.screen_h - 250))
        else:
            # Diagonal Web Swing across screen
            if app_x:
                self.target_x = max(self.screen_x + margin, min(app_x + random.randint(30, max(40, app_w - 180)), self.screen_x + self.screen_w - 160 - margin))
                self.target_y = max(self.screen_y + margin, min(app_y + random.randint(15, max(30, app_h - 220)), self.screen_y + self.screen_h - 200 - margin))
            else:
                max_x = max(self.screen_x, self.screen_x + self.screen_w - 160 - margin)
                max_y = max(self.screen_y, self.screen_y + self.screen_h - 200 - margin)
                self.target_x = random.randint(self.screen_x + margin, max_x)
                self.target_y = random.randint(self.screen_y + margin, max_y)

        self._is_zip_active = False

    def _sync_pet_state(self, updates: dict):
        """Push state updates directly to Chromium JS engine with zero socket/HTTP latency."""
        update_pet_state(updates)
        try:
            if not hasattr(self, '_last_js_updates'):
                self._last_js_updates = None
            if updates == self._last_js_updates and not updates.get("web_shoot_trigger"):
                return
            self._last_js_updates = dict(updates)
            import json
            js_code = f"if(window.updatePetStateDirect) window.updatePetStateDirect({json.dumps(updates)});"
            self.web_view.page().runJavaScript(js_code)
        except Exception:
            pass

    def _update_wander_position(self):
        if PET_STATE.get("open_chat_window"):
            chat_ts = PET_STATE.get("chat_ts", 0)
            if getattr(self, "_last_open_chat_ts", 0) != chat_ts:
                self._last_open_chat_ts = chat_ts
                PET_STATE["open_chat_window"] = False
                self.open_chat_window()

        if getattr(self, '_is_shoot_busy', False):
            return  # Strict constraint: Zero vertical/diagonal movement during web shooting!

        if PET_STATE.get("pet_mode") == "SLEEP":
            if self._is_zip_active:
                self.setGeometry(int(self.char_x), int(self.char_y), 180, 230)
                self._is_zip_active = False
            self._sync_pet_state({
                "motion_state": "SLEEP",
                "is_moving": False,
                "web_anchor_x": None,
                "web_anchor_y": None,
                "char_rel_x": None,
                "char_rel_y": None
            })
            return

        if not self.is_wandering or self.is_dragging or self.control_panel.isVisible():
            if self._is_zip_active or self.width() != 160 or self.height() != 200:
                self.setGeometry(int(self.char_x), int(self.char_y), 180, 230)
                self._is_zip_active = False
            self._sync_pet_state({
                "motion_state": "IDLE",
                "is_moving": False,
                "web_anchor_x": None,
                "web_anchor_y": None,
                "char_rel_x": None,
                "char_rel_y": None
            })
            return

        if self.pause_ticks > 0:
            self.pause_ticks -= 1
            current_motion = "LAND" if self.pause_ticks > 30 else "IDLE"

            rel_x = None
            rel_y = None
            if self._is_zip_active:
                rel_x = (self.char_x - self._zip_win_l) + 80
                rel_y = (self.char_y - self._zip_win_t) + 110

                if self.pause_ticks == 0:
                    self.setGeometry(int(self.char_x), int(self.char_y), 180, 230)
                    self._is_zip_active = False
                    rel_x = None
                    rel_y = None

            self._sync_pet_state({
                "motion_state": current_motion,
                "is_moving": False,
                "web_anchor_x": None,
                "web_anchor_y": None,
                "char_rel_x": rel_x,
                "char_rel_y": rel_y
            })
            if self.pause_ticks == 0:
                self._pick_new_wander_target()
            return

        curr_x = self.char_x
        curr_y = self.char_y
        dx = self.target_x - curr_x
        dy = self.target_y - curr_y
        dist = (dx**2 + dy**2) ** 0.5

        if dist < 14:
            self.char_x = self.target_x
            self.char_y = self.target_y
            self.pause_ticks = random.randint(220, 480)  # Calm rest pause between movements (3.6s - 8.0s)

            rel_x = None
            rel_y = None
            if self._is_zip_active:
                rel_x = (self.target_x - self._zip_win_l) + 80
                rel_y = (self.target_y - self._zip_win_t) + 110

            self._sync_pet_state({
                "motion_state": "LAND",
                "is_moving": False,
                "web_anchor_x": None,
                "web_anchor_y": None,
                "char_rel_x": rel_x,
                "char_rel_y": rel_y
            })
            return
        else:
            import math
            angle_deg = math.degrees(math.atan2(dy, dx))
            heading = 1 if dx >= 0 else -1
            self._heading_dir = heading
            vec_x = dx / dist
            vec_y = dy / dist

            if abs(dy) < 5:  # Pure Horizontal patrol
                if self._is_zip_active:
                    self.setGeometry(int(self.char_x), int(self.char_y), 180, 230)
                    self._is_zip_active = False

                is_sprint = dist >= 220
                motion = "SPRINT" if is_sprint else "WALK"
                speed = 1.0 if is_sprint else 0.55  # Relaxed, smooth grounded walk & sprint
                self.char_x += vec_x * speed
                self.char_y += vec_y * speed
                self.move(int(self.char_x), int(self.char_y))

                self._sync_pet_state({
                    "motion_state": motion,
                    "heading_dir": heading,
                    "move_angle": angle_deg,
                    "vector_x": vec_x,
                    "vector_y": vec_y,
                    "web_anchor_x": None,
                    "web_anchor_y": None,
                    "char_rel_x": None,
                    "char_rel_y": None,
                    "is_moving": True
                })
            else:  # Vertical or Diagonal Web Zip
                motion = "WEB_UP" if (abs(dx) < 5 and dy < 0) else ("WEB_DOWN" if abs(dx) < 5 else "WEB_DIAGONAL")
                speed = min(7.5, max(3.8, dist * 0.035))  # Smooth, graceful cinematic web swing pull

                # Calculate trajectory bounding box ONCE at zip start to preserve Windows DWM transparency
                pad = 50
                win_l = int(min(curr_x, self.target_x) - pad)
                win_t = int(min(curr_y, self.target_y) - pad)
                win_w = int(max(curr_x + 160, self.target_x + 160) - win_l + pad)
                win_h = int(max(curr_y + 200, self.target_y + 200) - win_t + pad)

                if not self._is_zip_active:
                    self.setGeometry(win_l, win_t, win_w, win_h)
                    self._zip_win_l = win_l
                    self._zip_win_t = win_t
                    self._is_zip_active = True

                self.char_x += vec_x * speed
                self.char_y += vec_y * speed

                rel_char_x = (self.char_x - self._zip_win_l) + 80
                rel_char_y = (self.char_y - self._zip_win_t) + 110
                anchor_x = (self.target_x - self._zip_win_l) + 80
                anchor_y = (self.target_y - self._zip_win_t) + 80

                self._sync_pet_state({
                    "motion_state": motion,
                    "heading_dir": heading,
                    "move_angle": angle_deg,
                    "vector_x": vec_x,
                    "vector_y": vec_y,
                    "web_anchor_x": anchor_x,
                    "web_anchor_y": anchor_y,
                    "char_rel_x": rel_char_x,
                    "char_rel_y": rel_char_y,
                    "is_moving": True
                })

    # ==============================================================================
    # Mouse Dragging Fallback (QMainWindow level)
    # ==============================================================================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.target_x = self.x()
            self.target_y = self.y()
            self.pause_ticks = 100
            event.accept()

    # ==============================================================================
    # Character / State Controls
    # ==============================================================================
    def set_character_style(self, style_code):
        style_code = str(style_code)
        update_pet_state({"character_style": style_code})
        logger.info(f"Character style changed to: {style_code}")
        self.web_view.page().runJavaScript(
            f"if (window.setCharacterStyle) window.setCharacterStyle('{style_code}');"
        )

    def toggle_wandering(self):
        self.is_wandering = not self.is_wandering
        if self.is_wandering:
            self._pick_new_wander_target()

    def reset_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.x() + screen.width() - self.width() - 40,
                  screen.y() + screen.height() - self.height() - 40)

    def open_chat_window(self):
        self.chat_window.show_beside_pet()

    def show_context_menu(self, pos=None):
        """Legacy stub — now handled by native control panel."""
        self._toggle_control_panel()


def kill_previous_pet_instances():
    """Find and terminate any old running instance of vrm_pet_gui."""
    current_pid = os.getpid()
    parent_pid = os.getppid()
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']
                if pid not in (current_pid, parent_pid):
                    cmdline = proc.info['cmdline'] or []
                    cmd_str = " ".join(cmdline).lower()
                    if "vrm_pet_gui" in cmd_str and ("python.exe" in cmd_str or "pythonw.exe" in cmd_str):
                        logger.info(f"Auto-killing previous pet instance PID: {pid}")
                        proc.kill()
            except Exception:
                pass
    except Exception:
        pass


def launch_vrm_pet():
    """Start Pet Server and launch PyQt5 3D Pet Overlay Window."""
    kill_previous_pet_instances()
    start_pet_server(host="127.0.0.1", port=8799)

    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "index.html"))
    ui_url = f"file:///{html_path.replace(os.sep, '/')}"

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings = QWebEngineSettings.globalSettings()
    settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
    settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
    settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
    settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
    settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)

    window = VRMPetWindow(ui_url)
    window.show()

    logger.info("3D VRM Desktop Pet GUI launched successfully.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launch_vrm_pet()
