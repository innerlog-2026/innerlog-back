from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    AI_SERVER_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

settings = Settings()