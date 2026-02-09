"""
Configuration Management
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm file .env trong thư mục chứa source code
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

class Config:
    """Configuration class"""
    
    # LLM Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Default LLM provider
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    
    # Vietnam Market APIs
    TCBS_API_BASE_URL = os.getenv("TCBS_API_BASE_URL", "https://apipubaws.tcbs.com.vn")
    SSI_API_KEY = os.getenv("SSI_API_KEY")
    SSI_API_SECRET = os.getenv("SSI_API_SECRET")
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
