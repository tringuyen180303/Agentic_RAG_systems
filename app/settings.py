from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    model_name: str = "llama3:latest"   # pull once on start-up
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    collection: str = "docs"

    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",        # ← ignore any other LANGFUSE_* vars
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
