"""
TechMart AI Customer Support — Configuration

This file defines all the settings the backend needs to run:
which LLM provider to talk to, database location, auth secrets,
RAG (retrieval) tuning, email, and WhatsApp credentials.

Every setting can be overridden by an environment variable (usually
set in a .env file), and falls back to a sensible default otherwise.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from a .env file (if one exists) into the environment
load_dotenv()

# Project root folder — two levels up from this file (backend/config.py -> project root)
BASE_DIR = Path(__file__).parent.parent


class Settings:
    
    # ------------------------------------------------------------------
    # App metadata
    # ------------------------------------------------------------------
    APP_NAME: str = "TechMart AI Support"

    APP_VERSION: str = "1.0.0"

    # DEBUG is True only if the DEBUG env var is literally the string "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


    # ------------------------------------------------------------------
    # LLM Provider selection
    # ------------------------------------------------------------------
    # Set LLM_PROVIDER to: groq | openai | ollama | anthropic
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")


    # ------------------------------------------------------------------
    # Groq settings (used when LLM_PROVIDER = "groq")
    # ------------------------------------------------------------------
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"


    # ------------------------------------------------------------------
    # OpenAI settings (used when LLM_PROVIDER = "openai")
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    OPENAI_BASE_URL: str = "https://api.openai.com/v1"


    # ------------------------------------------------------------------
    # Anthropic Claude settings
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")


    # ------------------------------------------------------------------
    # Ollama settings (for running models locally, no API key needed)
    # ------------------------------------------------------------------
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")


    # ------------------------------------------------------------------
    # Embedding model — turns text into vectors for similarity search
    # ------------------------------------------------------------------
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


    # ------------------------------------------------------------------
    # Database connection string (defaults to a local SQLite file)
    # ------------------------------------------------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/customer_support.db")


    # ------------------------------------------------------------------
    # Auth — JWT signing secret and token lifetime
    # ------------------------------------------------------------------
    # NOTE: change SECRET_KEY in production, this default is not secure
    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        
        raise ValueError("SECRET_KEY environment variable is required.")

    ALGORITHM: str = "HS256"

    # How long a login token stays valid, in minutes (default: 24 hours)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


    # ------------------------------------------------------------------
    # RAG (Retrieval-Augmented Generation) tuning
    # ------------------------------------------------------------------
    # Folder containing the raw knowledge base documents (FAQs, policies, etc.)
    KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "knowledge_base"

    # Folder where the FAISS vector index is saved/loaded from
    VECTOR_STORE_PATH: Path = BASE_DIR / "backend" / "vectorstore" / "faiss_index"

    # How many characters go into each text chunk before embedding
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "600"))

    # How many characters consecutive chunks overlap by (keeps context continuous)
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "80"))

    # How many top-matching chunks to retrieve per query
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "4"))


    # ------------------------------------------------------------------
    # LLM generation parameters
    # ------------------------------------------------------------------
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "600"))

    # Higher = more random/creative, lower = more focused/deterministic
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))


    # ------------------------------------------------------------------
    # Email (SMTP) settings, used for sending support notifications
    # ------------------------------------------------------------------
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")

    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))

    SMTP_USER: str = os.getenv("SMTP_USER", "")

    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@techmartelectronics.com")


    # ------------------------------------------------------------------
    # WhatsApp messaging via Twilio
    # ------------------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")

    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")

    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


    # ------------------------------------------------------------------
    # Company branding, shown in template responses / emails
    # ------------------------------------------------------------------
    COMPANY_NAME: str = "TechMart Electronics"

    COMPANY_TAGLINE: str = "Your Premium Electronics Partner"

    SUPPORT_PHONE: str = "1-800-TECHMART"

    def get_llm_config(self) -> dict:
        
        """
        Return the API key, base URL, and model name for whichever
        LLM_PROVIDER is currently configured.

        This lets the rest of the codebase call one function instead of
        checking LLM_PROVIDER everywhere it needs provider details.
        """

        if self.LLM_PROVIDER == "groq":

            # Groq: fast inference, OpenAI-compatible API
            return {
                
                "api_key": self.GROQ_API_KEY,
                
                "base_url": self.GROQ_BASE_URL,
                
                "model": self.GROQ_MODEL
                
            }

        elif self.LLM_PROVIDER == "openai":

            # OpenAI: standard GPT models
            return {
                
                "api_key": self.OPENAI_API_KEY,
                
                "base_url": self.OPENAI_BASE_URL,
                
                "model": self.OPENAI_MODEL
                
            }

        elif self.LLM_PROVIDER == "ollama":

            # Ollama runs locally, so no real API key is required —
            # the string "ollama" is just a placeholder value
            return {
                
                "api_key": "ollama",
                
                "base_url": self.OLLAMA_BASE_URL,
                
                "model": self.OLLAMA_MODEL
                
            }

        else:

            # Unknown/unset provider — fall back to mock mode so the
            # app still runs (using template responses) without a key
            return {
                
                "api_key": "", 
                
                "base_url": "", 
                
                "model": "mock"
                
                }


# Single shared settings instance, imported everywhere else in the app
settings = Settings()
