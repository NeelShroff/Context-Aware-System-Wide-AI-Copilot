# Context-Aware System-Wide AI Writing Copilot (Windows)

A production-grade, context-aware AI writing layer for Windows powered by **AutoHotkey v2**, **Python**, and **Groq API** (`openai/gpt-oss-120b`).

Press **Ctrl + Alt + E** anywhere in Windows to automatically capture your selection, infer what application and scenario you are in, intelligently rewrite or engineer the text using an LLM, paste the updated text, and immediately restore your original clipboard intact.

---

## Key Features

1. **AI Prompt Engineering Mode**:
   - Automatically activates whenever you are in an AI application or chat interface (e.g. **Antigravity**, **ChatGPT**, **Claude**, **Cursor**, **Windsurf**, **GitHub Copilot**, **OpenWebUI**, **LM Studio**, **Ollama**).
   - Transforms raw notes into structured, expert-level AI prompts optimized for maximum LLM performance (clarity, constraints, deterministic outputs, zero fluff, edge cases, acceptance criteria).

2. **Adaptive Writing Scenarios**:
   - **WhatsApp / Personal Chat**: Preserves personality, humor, and casual language; fixes grammar naturally without corporate speak.
   - **Slack / Teams**: Keeps messages concise, direct, professional yet conversational.
   - **Email**: Formats polished, structured business communication.
   - **GitHub / Jira**: Transforms rough notes into structured Bug Reports / Issues (`### Summary`, `### Expected Behavior`, `### Actual Behavior`, `### Steps to Reproduce`).
   - **Source Code**: Keeps executable code syntax 100% untouched; only improves comments and docstrings.
   - **Technical Documentation**: Retains technical terms and preserves Markdown syntax.

3. **Guaranteed Clipboard Protection**:
   - The user's original clipboard content is backed up before copying and restored after pasting, preventing clipboard history loss.

4. **Instant Visual Feedback**:
   - Non-stealing floating toast notification pill showing real-time status:
     `✨ Understanding context...` → `✨ Improving...` → `✅ Done`

---

## Requirements

- **Windows 10 / 11**
- **AutoHotkey v2.0+**
- **Python 3.10+**
- **Groq API Key** (or any OpenAI-compatible API key)

---

## Setup & Configuration

1. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=openai/gpt-oss-120b
   ```

2. **Install Python Dependencies** (if needed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Unit Tests**:
   ```bash
   python -m unittest discover tests
   ```

---

## How to Run

1. Double-click `run_copilot.cmd` or launch `copilot.ahk` with AutoHotkey v2.
2. Select any text in Windows.
3. Press **Ctrl + Alt + E**.
4. The floating indicator will show progress and replace your text automatically.
