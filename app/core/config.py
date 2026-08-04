from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    AI_SERVER_URL: str = "http://localhost:8000"
    # 백엔드와 AI 서버가 공유하는 음성 파일 볼륨 경로.
    # AI 서버에 넘기는 audio_file_path가 이 경로 기준이므로 두 프로세스가 동일하게 마운트해야 함.
    AUDIO_UPLOAD_DIR: str = "/uploads/audio"

    class Config:
        env_file = ".env"

settings = Settings()