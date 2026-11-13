from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"   # ignore unknown env vars
    )

    DATABASE_URL: str
    JWT_SECRET: str
    GROQ_API_KEY: str
    GEMINI_API_KEY: str = ""    # required for frontend tasks
    ANTHROPIC_API_KEY: str = "" # fallback for frontend tasks
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    VERCEL_TOKEN: str = ""      # enables the Deploy button (vercel.com/account/tokens)
    VERCEL_TEAM_ID: str = ""    # optional: deploy into a team instead of the token's personal account
    # Optional: creates/updates a developer account (unlimited credits) at startup.
    # Set both on the host; never commit real values.
    DEV_ACCOUNT_EMAIL: str = ""
    DEV_ACCOUNT_PASSWORD: str = ""

    # --- Sketch Studio (merged from Sketch2UI) ---
    # Text LLM for tidying a detected sketch and fixing accessibility problems: any
    # OpenAI-compatible server. Left unset, LLM_API_KEY falls back to GROQ_API_KEY.
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_API_KEY: str | None = None
    LLM_CODE_MODEL: str = "openai/gpt-oss-120b"
    LLM_VISION_MODEL: str = ""   # optional OpenAI-compatible vision model; Claude reads sketches by default
    # Only used when the optional detector is installed (requirements-vision.txt)
    OCR_MODEL: str = "PP-OCRv6_medium"
    OCR_ENGINE: str = "onnxruntime"

settings = Settings()
