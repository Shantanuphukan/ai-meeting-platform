from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Meeting Minutes Platform"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "meeting_minutes_system"

    DEEPGRAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    TORONGOXETU_HTTP_URL: str = "http://127.0.0.1:8002/transcribe"
    TORONGOXETU_AUTH_TOKEN: str = ""
    TORONGOXETU_MIN_CHUNK_MS: int = 700
    TORONGOXETU_MAX_CHUNK_MS: int = 1300
    TORONGOXETU_OVERLAP_MS: int = 320
    TORONGOXETU_HTTP_TIMEOUT_SEC: int = 60

    INDICCONFORMER_API_KEY: str = ""
    INDICCONFORMER_WS_URL: str = ""
    INDICCONFORMER_HTTP_URL: str = ""

    ENABLE_INDIC_STREAMING: bool = False
    ENABLE_TORONGOXETU_REFINEMENT: bool = True
    DEFAULT_MIX_FALLBACK_ENGINE: str = "torongoxetu"

    WHISPER_MODEL: str = "base"
    STORAGE_TEMP_AUDIO: str = "storage/temp_audio"
    STORAGE_EXPORTS: str = "storage/exports"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()