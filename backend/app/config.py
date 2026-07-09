from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "gemma2-9b-it"
    groq_context_model: str = "llama-3.3-70b-versatile"
    database_url: str = "sqlite:///./hcp_crm.db"
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
