from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str
    DATABASE_NAME: str = "onedesk"

    LLM_PROVIDER: str = "gemini"


    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.5-flash"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    SUPABASE_BUCKET: str = "onedesk-knowledge"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()