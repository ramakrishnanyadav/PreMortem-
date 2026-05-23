from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Core API Keys
    GROQ_API_KEY: str = Field(default="", description="Groq API key for reasoning engine")
    GITHUB_TOKEN: str = Field(default="", description="GitHub token for API access")
    
    # Optional but good to have
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis connection string")
    
    # Environment config
    ENVIRONMENT: str = Field(default="development", description="Environment mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
