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

settings = Settings()
