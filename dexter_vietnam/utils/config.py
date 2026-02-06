"""
Configuration Management
TODO: Load and validate environment variables
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class"""
    
    # LLM Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Vietnam Market APIs
    TCBS_API_BASE_URL = os.getenv("TCBS_API_BASE_URL", "https://apipubaws.tcbs.com.vn")
    SSI_API_KEY = os.getenv("SSI_API_KEY")
    SSI_API_SECRET = os.getenv("SSI_API_SECRET")
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
