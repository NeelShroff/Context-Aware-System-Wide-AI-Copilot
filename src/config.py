import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in parent directory or current directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    
    # Timeout in seconds for LLM call
    TIMEOUT_SECONDS: float = float(os.getenv("TIMEOUT_SECONDS", "8.0"))
    
    # Maximum retries on API failure
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "1"))

config = Config()
