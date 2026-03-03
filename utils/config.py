"""
Configuration Management
"""
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Config:
    """Configuration class"""

    # LLM Settings (OpenRouter only)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # Default LLM model (via OpenRouter)
    LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

    # Vietnam Market APIs
    TCBS_API_BASE_URL = os.getenv("TCBS_API_BASE_URL", "https://apipubaws.tcbs.com.vn")
    SSI_API_KEY = os.getenv("SSI_API_KEY")
    SSI_API_SECRET = os.getenv("SSI_API_SECRET")

    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = Config()
