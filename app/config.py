from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    riot_api_key: str
    riot_region: str
    
    # Firebase settings
    firebase_service_account_key: str = "serviceAccountKey.json"
    firebase_project_id: str
    firebase_database_url: str

    class Config:
        env_file = ".env"

settings = Settings()
